#
#   Copyright © 2023 Josep Maria Viñolas Auquer, Alberto Larraz Dalmases
#
#   This file is part of IsardVDI.
#
#   IsardVDI is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or (at your
#   option) any later version.
#
#   IsardVDI is distributed in the hope that it will be useful, but WITHOUT ANY
#   WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#   FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
#   details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with IsardVDI. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import time
import traceback
import uuid
from datetime import datetime, timedelta

import bcrypt
from cachetools import TTLCache, cached
from isardvdi_common.api_exceptions import Error

from api import app

from .bookings.api_booking import Bookings

apib = Bookings()

from .api_desktop_events import category_delete, group_delete, user_delete
from .quotas import Quotas

quotas = Quotas()


from string import ascii_lowercase, digits

from jose import jwt
from rethinkdb import RethinkDB

from .flask_rethink import RDB

r = RethinkDB()
db = RDB(app)
db.init_app(app)


from ..libv2.api_user_storage import (
    isard_user_storage_add_user,
    isard_user_storage_update_user,
    isard_user_storage_update_user_quota,
    user_storage_quota,
)
from .api_admin import (
    change_category_items_owner,
    change_group_items_owner,
    change_user_items_owner,
)
from .helpers import (
    GetAllTemplateDerivates,
    _check,
    _parse_desktop,
    _random_password,
    gen_payload_from_user,
)


@cached(cache=TTLCache(maxsize=100, ttl=60))
def get_user(user_id):
    with app.app_context():
        return r.table("users").get(user_id).run(db.conn)


def check_category_domain(category_id, domain):
    with app.app_context():
        allowed_domain = (
            r.table("categories")
            .get(category_id)
            .pluck("allowed_domain")
            .run(db.conn)
            .get("allowed_domain")
        )
    allowed = not allowed_domain or domain == allowed_domain
    if not allowed:
        raise Error(
            "forbidden",
            "Register domain does not match category allowed domain",
            traceback.format_exc(),
        )


class ApiUsers:
    def Jwt(self, user_id, minutes=240):
        return {
            "jwt": jwt.encode(
                {
                    "exp": datetime.utcnow() + timedelta(minutes=minutes),
                    "kid": "isardvdi",
                    "data": gen_payload_from_user(user_id),
                },
                os.environ.get("API_ISARDVDI_SECRET"),
                algorithm="HS256",
            )
        }

    def Login(self, user_id, user_passwd, provider="local", category_id="default"):
        with app.app_context():
            user = r.table("users").get(user_id).run(db.conn)
        if user is None:
            raise Error("unauthorized", "", traceback.format_exc())
        if not user.get("active", False):
            raise Error(
                "unauthorized",
                "User " + user_id + " is disabled",
                traceback.format_exc(),
            )

        pw = Password()
        if pw.valid(user_passwd, user["password"]):
            user = {
                "user_id": user["id"],
                "role_id": user["role"],
                "category_id": user["category"],
                "group_id": user["group"],
                "username": user["username"],
                "email": user["email"],
                "photo": user["photo"],
            }
            return user_id, jwt.encode(
                {
                    "exp": datetime.utcnow() + timedelta(hours=4),
                    "kid": "isardvdi",
                    "data": user,
                },
                os.environ.get("API_ISARDVDI_SECRET"),
                algorithm="HS256",
            )
        raise Error(
            "unauthorized",
            "Invalid login credentials for user_id " + user_id,
            traceback.format_exc(),
        )

    def Config(self, payload):
        show_bookings_button = (
            True
            if payload["role_id"] == "admin"
            or os.environ.get("FRONTEND_SHOW_BOOKINGS") == "True"
            else False
        )
        frontend_show_temporal_tab = (
            True
            if os.environ.get("FRONTEND_SHOW_TEMPORAL") == None
            else os.environ.get("FRONTEND_SHOW_TEMPORAL") == "True"
        )
        isard_user_storage_update_user_quota(payload["user_id"])
        return {
            **{
                "show_bookings_button": show_bookings_button,
                "documentation_url": os.environ.get(
                    "FRONTEND_DOCS_URI", "https://isard.gitlab.io/isardvdi-docs/"
                ),
                "show_temporal_tab": frontend_show_temporal_tab,
            },
        }

    def Get(self, user_id, get_quota=False):
        with app.app_context():
            try:
                user = (
                    r.table("users")
                    .get(user_id)
                    .merge(
                        lambda d: {
                            "category_name": r.table("categories").get(d["category"])[
                                "name"
                            ],
                            "group_name": r.table("groups").get(d["group"])["name"],
                            "role_name": r.table("roles").get(d["role"])["name"],
                        }
                    )
                    .without("password")
                    .run(db.conn)
                )
            except:
                raise Error(
                    "not_found",
                    "Not found user_id " + user_id,
                    traceback.format_exc(),
                )
        if get_quota:
            user = {**user, **quotas.Get(user_id)}
        return user

    def GetByProviderCategoryUID(self, provider, category, uid):
        with app.app_context():
            user = list(
                r.table("users")
                .get_all([uid, category, provider], index="uid_category_provider")
                .run(db.conn)
            )
        return user

    def list_users(self, nav, category_id=None):
        query = r.table("users")
        if category_id:
            query = query.get_all(category_id, index="category")

        query = query.pluck(
            "id",
            "active",
            "name",
            "provider",
            "category",
            "uid",
            "username",
            "role",
            "group",
            "secondary_groups",
            "email",
            "accessed",
            {"vpn": {"wireguard": {"connected": True}}},
            {"user_storage": {"provider_quota": {"used": True, "relative": True}}},
        )
        if nav == "management":
            query = query.merge(
                lambda user: {
                    "group_name": r.table("groups").get(user["group"])["name"],
                    "role_name": r.table("roles").get(user["role"])["name"],
                    "category_name": r.table("categories").get(user["category"])[
                        "name"
                    ],
                    "secondary_groups_names": r.table("groups")
                    .get_all(r.args(user["secondary_groups"]))["name"]
                    .coerce_to("array"),
                }
            )
        if nav == "quotas_limits":
            query = query.pluck(
                "id",
                "name",
                "username",
                "role",
                "category",
                "group",
                {"user_storage": {"provider_quota": {"used": True, "relative": True}}},
            ).merge(
                lambda user: {
                    "group_name": r.table("groups").get(user["group"])["name"],
                    "role_name": r.table("roles").get(user["role"])["name"],
                    "category_name": r.table("categories").get(user["category"])[
                        "name"
                    ],
                    "desktops": r.table("domains")
                    .get_all(["desktop", user["id"]], index="kind_user")
                    .pluck("id")
                    .count(),
                    "templates": r.table("domains")
                    .get_all(["template", user["id"]], index="kind_user")
                    .pluck("id")
                    .count(),
                    "media_size": (
                        r.table("media")
                        .get_all(user["id"], index="user")
                        .pluck({"progress": "total_bytes"})
                        .sum(lambda size: size["progress"]["total_bytes"].default(0))
                    )
                    / 1073741824,
                    "domains_size": (
                        r.table("storage")
                        .get_all([user["id"], "ready"], index="user_status")
                        .pluck({"qemu-img-info": "actual-size"})
                        .sum(
                            lambda size: size["qemu-img-info"]["actual-size"].default(0)
                        )
                    )
                    / 1073741824,
                }
            )
        with app.app_context():
            return list(query.run(db.conn))

    def list_categories(self, nav, category_id=False):
        query = []
        if nav == "management":
            with app.app_context():
                if category_id:
                    query = (
                        r.table("categories")
                        .get_all(category_id)
                        .without("quota", "limits")
                    )
                else:
                    query = r.table("categories").without("quota", "limits")

        elif nav == "quotas_limits":
            with app.app_context():
                if category_id:
                    query = (
                        r.table("categories")
                        .get_all(category_id)
                        .merge(
                            {
                                "media_size": (
                                    r.table("media")
                                    .get_all(category_id, index="category")
                                    .pluck({"progress": "total_bytes"})
                                    .sum(
                                        lambda size: size["progress"][
                                            "total_bytes"
                                        ].default(0)
                                    )
                                )
                                / 1073741824,
                                "domains_size": (
                                    r.table("users")
                                    .get_all(category_id, index="category")
                                    .pluck("id")
                                    .merge(
                                        lambda user: {
                                            "storage": r.table("storage")
                                            .get_all(
                                                [user["id"], "ready"],
                                                index="user_status",
                                            )
                                            .pluck({"qemu-img-info": "actual-size"})
                                            .sum(
                                                lambda right: right["qemu-img-info"][
                                                    "actual-size"
                                                ].default(0)
                                            ),
                                        }
                                    )
                                    .sum("storage")
                                )
                                / 1073741824,
                            }
                        )
                    )

                else:
                    query = r.table("categories").merge(
                        lambda category: {
                            "media_size": (
                                r.table("media")
                                .get_all(category["id"], index="category")
                                .pluck({"progress": "total_bytes"})
                                .sum(
                                    lambda size: size["progress"][
                                        "total_bytes"
                                    ].default(0)
                                )
                            )
                            / 1073741824,
                            "domains_size": (
                                r.table("users")
                                .get_all(category["id"], index="category")
                                .pluck("id")
                                .merge(
                                    lambda user: {
                                        "storage": r.table("storage")
                                        .get_all(
                                            [user["id"], "ready"],
                                            index="user_status",
                                        )
                                        .pluck({"qemu-img-info": "actual-size"})
                                        .sum(
                                            lambda right: right["qemu-img-info"][
                                                "actual-size"
                                            ].default(0)
                                        ),
                                    }
                                )
                                .sum("storage")
                            )
                            / 1073741824,
                        }
                    )

        return list(query.run(db.conn))

    def list_groups(self, nav, category_id=False):
        query = []
        if nav == "management":
            if category_id:
                query = (
                    r.table("groups")
                    .get_all(category_id, index="parent_category")
                    .without("quota", "limits")
                    .merge(
                        lambda group: {
                            "linked_groups_names": r.table("groups")
                            .get_all(r.args(group["linked_groups"]))["name"]
                            .coerce_to("array")
                        }
                    )
                )

            else:
                query = (
                    r.table("groups")
                    .without("quota", "limits")
                    .merge(
                        lambda group: {
                            "linked_groups_names": r.table("groups")
                            .get_all(r.args(group["linked_groups"]))["name"]
                            .coerce_to("array"),
                            "parent_category_name": r.table("categories").get(
                                group["parent_category"]
                            )["name"],
                        }
                    )
                )

        elif nav == "quotas_limits":
            if category_id:
                query = (
                    r.table("groups")
                    .get_all(category_id, index="parent_category")
                    .merge(
                        lambda group: {
                            "linked_groups_data": r.table("groups")
                            .get_all(r.args(group["linked_groups"]))
                            .pluck("id", "name")
                            .coerce_to("array"),
                            "media_size": (
                                r.table("media")
                                .get_all(group["id"], index="group")
                                .pluck({"progress": "total_bytes"})
                                .sum(
                                    lambda size: size["progress"][
                                        "total_bytes"
                                    ].default(0)
                                )
                            )
                            / 1073741824,
                            "domains_size": (
                                r.table("users")
                                .get_all(group["id"], index="group")
                                .pluck("id")
                                .merge(
                                    lambda user: {
                                        "storage": r.table("storage")
                                        .get_all(
                                            [user["id"], "ready"], index="user_status"
                                        )
                                        .pluck({"qemu-img-info": "actual-size"})
                                        .sum(
                                            lambda right: right["qemu-img-info"][
                                                "actual-size"
                                            ].default(0)
                                        ),
                                    }
                                )
                                .sum("storage")
                            )
                            / 1073741824,
                        }
                    )
                    .without(
                        "enrollment", "external_app_id", "external_gid", "linked_groups"
                    )
                )
            else:
                query = (
                    r.table("groups")
                    .merge(
                        lambda group: {
                            "linked_groups_data": r.table("groups")
                            .get_all(r.args(group["linked_groups"]))
                            .pluck("id", "name")
                            .coerce_to("array"),
                            "parent_category_name": r.table("categories").get(
                                group["parent_category"]
                            )["name"],
                            "media_size": (
                                r.table("media")
                                .get_all(group["id"], index="group")
                                .pluck({"progress": "total_bytes"})
                                .sum(
                                    lambda size: size["progress"][
                                        "total_bytes"
                                    ].default(0)
                                )
                            )
                            / 1073741824,
                            "domains_size": (
                                r.table("users")
                                .get_all(group["id"], index="group")
                                .pluck("id")
                                .merge(
                                    lambda user: {
                                        "storage": r.table("storage")
                                        .get_all(
                                            [user["id"], "ready"], index="user_status"
                                        )
                                        .pluck({"qemu-img-info": "actual-size"})
                                        .sum(
                                            lambda right: right["qemu-img-info"][
                                                "actual-size"
                                            ].default(0)
                                        ),
                                    }
                                )
                                .sum("storage")
                            )
                            / 1073741824,
                        }
                    )
                    .without(
                        "enrollment", "external_app_id", "external_gid", "linked_groups"
                    )
                )

        return list(query.run(db.conn))

    # this method is needed for user auto-registering
    # It will get the quota from the user group provided
    def Create(
        self,
        provider,
        category_id,
        user_uid,
        user_username,
        name,
        role_id,
        group_id,
        password=False,
        encrypted_password=False,
        photo="",
        email="",
    ):
        # password=False generates a random password
        with app.app_context():
            user_id = str(uuid.uuid4())
            if r.table("users").get(user_id).run(db.conn) != None:
                raise Error(
                    "conflict",
                    "Already exists user_id " + user_id,
                    traceback.format_exc(),
                )

            if r.table("roles").get(role_id).run(db.conn) is None:
                raise Error(
                    "not_found",
                    "Not found role_id " + role_id + " for user_id " + user_id,
                    traceback.format_exc(),
                )

            if r.table("categories").get(category_id).run(db.conn) is None:
                raise Error(
                    "not_found",
                    "Not found category_id " + category_id + " for user_id " + user_id,
                    traceback.format_exc(),
                )

            group = r.table("groups").get(group_id).run(db.conn)
            if group is None:
                raise Error(
                    "not_found",
                    "Not found group_id " + group_id + " for user_id " + user_id,
                    traceback.format_exc(),
                )

            if password == False:
                password = _random_password()
            else:
                bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
                    "utf-8"
                )
            if encrypted_password != False:
                password = encrypted_password

            user = {
                "id": user_id,
                "name": name,
                "uid": user_uid,
                "provider": provider,
                "active": True,
                "accessed": int(time.time()),
                "username": user_username,
                "password": password,
                "role": role_id,
                "category": category_id,
                "group": group_id,
                "email": email,
                "photo": photo,
                "default_templates": [],
                "quota": group["quota"],  # 10GB
                "secondary_groups": [],
            }
            if not _check(r.table("users").insert(user).run(db.conn), "inserted"):
                raise Error(
                    "internal_server",
                    "Unable to insert in database user_id " + user_id,
                    traceback.format_exc(),
                )
        isard_user_storage_add_user(user_id)
        return user_id

    def Update(self, user_ids, data):
        if data.get("password"):
            p = Password()
            data["password"] = p.encrypt(data["password"])

        with app.app_context():
            r.table("users").get_all(r.args(user_ids)).update(data).run(db.conn)
        for user_id in user_ids:
            isard_user_storage_update_user(
                user_id=user_id,
                email=data.get("email"),
                displayname=data.get("name"),
                role=data.get("role"),
                enabled=data.get("active"),
            )

    def Templates(self, payload):
        try:
            with app.app_context():
                templates = (
                    r.table("domains")
                    .get_all(["template", payload["user_id"]], index="kind_user")
                    .order_by("name")
                    .pluck(
                        {
                            "id",
                            "name",
                            "allowed",
                            "enabled",
                            "kind",
                            "category",
                            "group",
                            "icon",
                            "image",
                            "user",
                            "description",
                            "status",
                        },
                        {"create_dict": {"hardware": {"disks": {"storage_id": True}}}},
                    )
                    .run(db.conn)
                )
            return templates
        except Exception:
            raise Error(
                "internal_server", "Internal server error", traceback.format_exc()
            )

    def Desktops(self, user_id):
        self.Get(user_id)
        try:
            with app.app_context():
                desktops = list(
                    r.table("domains")
                    .get_all(["desktop", user_id], index="kind_user")
                    .order_by("name")
                    .pluck(
                        [
                            "id",
                            "name",
                            "icon",
                            "image",
                            "user",
                            "group",
                            "category",
                            "status",
                            "description",
                            "parents",
                            "persistent",
                            "os",
                            "guest_properties",
                            "tag",
                            "tag_visible",
                            {"viewer": "guest_ip"},
                            {
                                "create_dict": {
                                    "hardware": ["interfaces", "videos", "disks"],
                                    "reservables": True,
                                }
                            },
                            "server",
                            "progress",
                            "booking_id",
                            "scheduled",
                            "tag",
                        ]
                    )
                    .run(db.conn)
                )
            return [
                _parse_desktop(desktop)
                for desktop in desktops
                if not desktop.get("tag")
                or desktop.get("tag")
                and desktop.get("tag_visible")
            ]
        except:
            raise Error(
                "internal_server",
                "Internal server error",
                traceback.format_exc(),
                description_code="generic_error",
            )

    def Desktop(self, desktop_id, user_id):
        self.Get(user_id)
        try:
            with app.app_context():
                desktop = (
                    r.table("domains")
                    .get(desktop_id)
                    .pluck(
                        [
                            "id",
                            "name",
                            "icon",
                            "image",
                            "user",
                            "group",
                            "category",
                            "status",
                            "description",
                            "parents",
                            "persistent",
                            "os",
                            "guest_properties",
                            "tag",
                            "tag_visible",
                            {"viewer": "guest_ip"},
                            {
                                "create_dict": {
                                    "hardware": ["interfaces", "videos"],
                                    "reservables": True,
                                }
                            },
                            "progress",
                            "booking_id",
                        ]
                    )
                    .run(db.conn)
                )
            if (
                not desktop.get("tag")
                or desktop.get("tag")
                and desktop.get("tag_visible")
            ):
                return _parse_desktop(desktop)
            else:
                raise Error(
                    "forbidden",
                    f"Desktop {desktop_id} is not visible to this user now.",
                    description_code="desktop_is_not_visible",
                )
        except:
            raise Error(
                "not_found",
                f"Desktop {desktop_id} not found",
                description_code="desktop_not_found",
            )

    def Delete(self, user_id, agent_id, delete_user):
        self.Get(user_id)
        change_user_items_owner("media", user_id)
        user_delete(agent_id, user_id, delete_user)

    def _delete_checks(self, item_ids, table):
        users = []
        groups = []
        desktops = []
        templates = []
        deployments = []
        media = []
        tags = []
        with app.app_context():
            if table == "user":
                users = list(
                    r.table("users")
                    .get_all(r.args(item_ids))
                    .pluck("id", "name", "username")
                    .run(db.conn)
                )
                deployments = list(
                    r.table("deployments")
                    .get_all(r.args(item_ids), index="user")
                    .pluck("id", "name", "user")
                    .merge(
                        lambda row: {
                            "user_name": r.table("users").get(row["user"])["name"],
                            "username": r.table("users").get(row["user"])["username"],
                        }
                    )
                    .run(db.conn)
                )
                tags = [deployment["id"] for deployment in deployments]
                desktops = desktops + list(
                    r.table("domains")
                    .get_all(r.args(tags), index="tag")
                    .pluck("id", "name", "kind", "user", "status", "parents")
                    .merge(
                        lambda d: {
                            "username": r.table("users").get(d["user"])["username"],
                            "user_name": r.table("users").get(d["user"])["name"],
                        }
                    )
                    .run(db.conn)
                )
            elif table in ["category", "group"]:
                users = list(
                    r.table("users")
                    .get_all(r.args(item_ids), index=table)
                    .pluck("id", "name", "username")
                    .run(db.conn)
                )
                users_ids = [user["id"] for user in users]
                deployments = list(
                    r.table("deployments")
                    .get_all(r.args(users_ids), index="user")
                    .pluck("id", "name", "user")
                    .merge(
                        lambda row: {
                            "user_name": r.table("users").get(row["user"])["name"],
                            "username": r.table("users").get(row["user"])["username"],
                        }
                    )
                    .run(db.conn)
                )
                tags = [deployment["id"] for deployment in deployments]
                desktops = desktops + list(
                    r.table("domains")
                    .get_all(r.args(tags), index="tag")
                    .pluck("id", "name", "kind", "user", "status", "parents")
                    .merge(
                        lambda d: {
                            "username": r.table("users").get(d["user"])["username"],
                            "user_name": r.table("users").get(d["user"])["name"],
                        }
                    )
                    .run(db.conn)
                )
                if table == "category":
                    groups = list(
                        r.table("groups")
                        .get_all(r.args(item_ids), index="parent_category")
                        .pluck("id", "name")
                        .run(db.conn)
                    )
                else:
                    groups = list(
                        r.table("groups")
                        .get_all(r.args(item_ids))
                        .pluck("id", "name")
                        .run(db.conn)
                    )

            desktops = desktops + list(
                r.table("domains")
                .get_all(r.args(item_ids), index=table)
                .filter({"kind": "desktop"})
                .pluck("id", "name", "kind", "user", "status", "parents")
                .merge(
                    lambda d: {
                        "username": r.table("users").get(d["user"])["username"],
                        "user_name": r.table("users").get(d["user"])["name"],
                    }
                )
                .run(db.conn)
            )
            templates = list(
                r.table("domains")
                .get_all(r.args(item_ids), index=table)
                .filter({"kind": "template"})
                .pluck("id", "name", "kind", "user", "category", "group")
                .merge(
                    lambda d: {
                        "username": r.table("users").get(d["user"])["username"],
                        "user_name": r.table("users").get(d["user"])["name"],
                    }
                )
                .run(db.conn)
            )
        domains_derivated = []
        for template in templates:
            domains_derivated = domains_derivated + GetAllTemplateDerivates(
                template["id"]
            )
        desktops = desktops + list(
            filter(lambda d: d["kind"] == "desktop", domains_derivated)
        )
        desktops = list({v["id"]: v for v in desktops}.values())
        templates = templates + list(
            filter(lambda d: d["kind"] == "template", domains_derivated)
        )
        templates = list({v["id"]: v for v in templates}.values())

        with app.app_context():
            media = list(
                r.table("media")
                .get_all(r.args(item_ids), index=table)
                .pluck("id", "name", "user")
                .merge(
                    lambda row: {
                        "user_name": r.table("users").get(row["user"])["name"],
                        "username": r.table("users").get(row["user"])["username"],
                    }
                )
                .run(db.conn)
            )

        return {
            "desktops": desktops,
            "templates": templates,
            "deployments": deployments,
            "media": media,
            "users": users,
            "groups": groups,
        }

    def _user_storage_delete_checks(self, user_id):
        with app.app_context():
            user_storage = (
                r.table("users").get(user_id).pluck("name", "user_storage").run(db.conn)
            )
            if user_storage.get("user_storage"):
                return {
                    "id": None,
                    "kind": "user_storage",
                    "user_name": user_storage.get("name"),
                    "name": str(user_storage_quota(user_id).get("used", 0)) + " MB",
                }

    @cached(TTLCache(maxsize=10, ttl=5))
    def OwnsDesktopViewerIP(self, user_id, category_id, role_id, guess_ip):
        try:
            with app.app_context():
                domains = list(
                    r.table("domains")
                    .get_all(guess_ip, index="guest_ip")
                    .filter(
                        lambda domain: r.expr(["Started", "Shutting-down"]).contains(
                            domain["status"]
                        )
                    )
                    .pluck("user", "category", "tag")
                    .run(db.conn)
                )
        except:
            app.logger.error(traceback.format_exc())
            raise Error(
                "forbidden",
                "Forbidden access to desktop viewer",
                traceback.format_exc(),
            )
        if not len(domains):
            raise Error(
                "bad_request",
                f"No desktop with requested guess_ip {guess_ip} to access viewer",
                traceback.format_exc(),
            )
        if len(domains) > 1:
            app.logger.error(traceback.format_exc())
            raise Error(
                "internal_server",
                "Two desktops with the same viewer guest_ip",
                traceback.format_exc(),
            )

        if role_id == "admin":
            return True
        elif role_id == "manager" and domains[0].get("category") == category_id:
            return True
        elif domains[0].get("user") == user_id:
            return True
        elif domains[0].get("tag"):
            with app.app_context():
                deployment_user_owner = (
                    r.table("deployments")
                    .get(domains[0].get("tag"))
                    .pluck("user")
                    .run(db.conn)
                ).get("user", None)
            if deployment_user_owner == user_id:
                return True

        raise Error(
            "forbidden",
            f"Forbidden access to user {user_id} to desktop {domains[0]} viewer",
            traceback.format_exc(),
        )

    @cached(TTLCache(maxsize=10, ttl=5))
    def OwnsDesktopViewerProxiesPort(
        self, user_id, category_id, role_id, proxy_video, proxy_hyper_host, port
    ):
        try:
            proxy_video_parts = proxy_video.split(":")
            if len(proxy_video_parts) == 2:
                proxy_video = proxy_video_parts[0]
                proxy_video_port = proxy_video_parts[1]
            else:
                proxy_video_port = "443"
            with app.app_context():
                domains = list(
                    r.table("domains")
                    .get_all(
                        [proxy_video, proxy_video_port, proxy_hyper_host],
                        index="proxies",
                    )
                    .filter(
                        lambda domain: r.expr(["Started", "Shutting-down"]).contains(
                            domain["status"]
                        )
                    )
                    .filter(r.row["viewer"]["ports"].contains(port))
                    .pluck("user", "category", "tag")
                    .run(db.conn)
                )
        except:
            raise Error(
                "forbidden",
                "Forbidden access to desktop viewer",
                traceback.format_exc(),
            )
        if not len(domains):
            raise Error(
                "bad_request",
                f"No desktop with requested parameters (proxy_video: {proxy_video}, proxy_hyper_host: {proxy_hyper_host}, port: {port}) to access viewer",
                traceback.format_exc(),
            )
        if len(domains) > 1:
            raise Error(
                "internal_server",
                "Two desktops with the same viewer guest_ip",
                traceback.format_exc(),
            )

        if role_id == "admin":
            return True
        elif role_id == "manager" and domains[0].get("category") == category_id:
            return True
        elif domains[0].get("user") == user_id:
            return True
        elif domains[0].get("tag"):
            with app.app_context():
                deployment_user_owner = (
                    r.table("deployments")
                    .get(domains[0].get("tag"))
                    .pluck("user")
                    .run(db.conn)
                ).get("user", None)
            if deployment_user_owner == user_id:
                return True

        raise Error(
            "forbidden",
            f"Forbidden access to user {user_id} to desktop {domains[0]} viewer",
            traceback.format_exc(),
        )

    def CodeSearch(self, code):
        with app.app_context():
            found = list(
                r.table("groups").filter({"enrollment": {"manager": code}}).run(db.conn)
            )
            if len(found) > 0:
                category = found[0]["parent_category"]  # found[0]['id'].split('_')[0]
                return {
                    "role": "manager",
                    "category": category,
                    "group": found[0]["id"],
                }
            found = list(
                r.table("groups")
                .filter({"enrollment": {"advanced": code}})
                .run(db.conn)
            )
            if len(found) > 0:
                category = found[0]["parent_category"]  # found[0]['id'].split('_')[0]
                return {
                    "role": "advanced",
                    "category": category,
                    "group": found[0]["id"],
                }
            found = list(
                r.table("groups").filter({"enrollment": {"user": code}}).run(db.conn)
            )
            if len(found) > 0:
                category = found[0]["parent_category"]  # found[0]['id'].split('_')[0]
                return {"role": "user", "category": category, "group": found[0]["id"]}
        raise Error(
            "not_found",
            "Code not found code:" + code,
            traceback.format_exc(),
            description_code="code_not_found",
        )

    def CategoryGet(self, category_id, all=False):
        with app.app_context():
            category = r.table("categories").get(category_id).run(db.conn)
        if not category:
            raise Error(
                "not_found",
                "Category not found category_id:" + category_id,
                traceback.format_exc(),
                description_code="category_not_found",
            )
        if not all:
            return {"name": category["name"]}
        else:
            return category

    def CategoryGetByName(self, category_name):
        with app.app_context():
            category = list(
                r.table("categories")
                .filter({"name": category_name.strip()})
                .run(db.conn)
            )
        if not category:
            raise Error(
                "not_found",
                "Category name " + category_name + " not found",
                traceback.format_exc(),
            )
        else:
            return category[0]

    def category_get_by_custom_url(self, custom_url):
        with app.app_context():
            category = list(
                r.table("categories")
                .filter({"custom_url_name": custom_url})
                .pluck("id", "name")
                .run(db.conn)
            )
        if not category:
            raise Error(
                "not_found",
                "Category with custom url " + custom_url + " not found",
                traceback.format_exc(),
            )
        else:
            return category[0]

    def category_get_custom_login_url(self, category_id):
        try:
            with app.app_context():
                category = (
                    r.table("categories")
                    .get(category_id)
                    .pluck("frontend", "custom_url_name")
                    .run(db.conn)
                )
            return "/login/" + category.get("custom_url_name")
        except:
            return "/login"

    ### USER Schema

    def CategoriesGet(self):
        with app.app_context():
            return list(
                r.table("categories")
                .pluck({"id", "name", "frontend"})
                .order_by("name")
                .run(db.conn)
            )

    def CategoriesFrontendGet(self):
        with app.app_context():
            return list(
                r.table("categories")
                .pluck({"id", "name", "frontend", "custom_url_name"})
                .filter({"frontend": True})
                .order_by("name")
                .run(db.conn)
            )

    def CategoryDelete(self, category_id, agent_id):
        change_category_items_owner("media", category_id)
        category_delete(agent_id, category_id)

    def GroupGet(self, group_id):
        with app.app_context():
            group = r.table("groups").get(group_id).run(db.conn)
        if not group:
            raise Error(
                "not_found",
                "Not found group_id " + group_id,
                traceback.format_exc(),
                description_code="group_not_found",
            )
        return group

    def GroupGetByNameCategory(self, group_name, category_id):
        with app.app_context():
            group = list(
                r.table("groups")
                .get_all(category_id, index="parent_category")
                .filter({"name": group_name})
                .run(db.conn)
            )
        if not group:
            raise Error(
                "not_found",
                "Not found group name " + group_name,
                traceback.format_exc(),
            )
        return group[0]

    def GroupsGet(self):
        return list(
            r.table("groups")
            .order_by("name")
            .merge(
                lambda group: {
                    "linked_groups_data": r.table("groups")
                    .get_all(r.args(group["linked_groups"]))
                    .pluck("id", "name")
                    .coerce_to("array"),
                }
            )
            .run(db.conn)
        )

    def GroupDelete(self, group_id, agent_id):
        # Check the group exists
        self.GroupGet(group_id)
        change_group_items_owner("media", group_id)
        group_delete(agent_id, group_id)

    def EnrollmentAction(self, data):
        if data["action"] == "disable":
            with app.app_context():
                r.table("groups").get(data["id"]).update(
                    {"enrollment": {data["role"]: False}}
                ).run(db.conn)
            return True
        if data["action"] == "reset":
            chars = digits + ascii_lowercase
        code = False
        while code == False:
            code = "".join([random.choice(chars) for i in range(6)])
            if self.enrollment_code_check(code) == False:
                with app.app_context():
                    r.table("groups").get(data["id"]).update(
                        {"enrollment": {data["role"]: code}}
                    ).run(db.conn)
                return code
        raise Error(
            "internal_server",
            "Unable to generate enrollment code",
            traceback.format_exc(),
            description_code="unable_to_gen_enrollment_code",
        )

    def enrollment_code_check(self, code):
        with app.app_context():
            found = list(
                r.table("groups").filter({"enrollment": {"manager": code}}).run(db.conn)
            )
            if len(found) > 0:
                category = found[0]["parent_category"]  # found[0]['id'].split('_')[0]
                return {
                    "code": code,
                    "role": "manager",
                    "category": category,
                    "group": found[0]["id"],
                }
            found = list(
                r.table("groups")
                .filter({"enrollment": {"advanced": code}})
                .run(db.conn)
            )
            if len(found) > 0:
                category = found[0]["parent_category"]  # found[0]['id'].split('_')[0]
                return {
                    "code": code,
                    "role": "advanced",
                    "category": category,
                    "group": found[0]["id"],
                }
            found = list(
                r.table("groups").filter({"enrollment": {"user": code}}).run(db.conn)
            )
            if len(found) > 0:
                category = found[0]["parent_category"]  # found[0]['id'].split('_')[0]
                return {
                    "code": code,
                    "role": "user",
                    "category": category,
                    "group": found[0]["id"],
                }
        return False

    def UpdateGroupQuota(
        self, group, quota, propagate, role=False, user_role="manager"
    ):
        category = self.CategoryGet(group["parent_category"], True)
        # Managers can't update a group quota with a higher value than its category quota
        if user_role == "manager":
            if category["quota"] != False:
                for k, v in category["quota"].items():
                    if quota and quota.get(k) and v < quota[k]:
                        raise Error(
                            "precondition_required",
                            "Can't update "
                            + group["name"]
                            + " "
                            + k
                            + " quota value with a higher value than its category quota",
                            traceback.format_exc(),
                        )

        # Can't update a group quota with a higher value than its category limit
        if category["limits"] != False:
            for k, v in category["limits"].items():
                if quota and quota.get(k) and v < quota[k]:
                    raise Error(
                        "precondition_required",
                        "Can't update "
                        + group["name"]
                        + " "
                        + k
                        + " quota value with a higher value than its category limit",
                        traceback.format_exc(),
                    )

        if not role:
            with app.app_context():
                r.table("groups").get(group["id"]).update({"quota": quota}).run(db.conn)

        if propagate or role:
            query = r.table("users").get_all(group["id"], index="group")
            if role:
                query = query.filter({"role": role})
            with app.app_context():
                query.update({"quota": quota}).run(db.conn)

    def UpdateCategoryQuota(self, category_id, quota, propagate, role=False):
        if not role:
            with app.app_context():
                r.table("categories").get(category_id).update({"quota": quota}).run(
                    db.conn
                )
        if propagate or role:
            with app.app_context():
                for group in list(
                    r.table("groups")
                    .get_all(category_id, index="parent_category")
                    .run(db.conn)
                ):
                    self.UpdateGroupQuota(group, quota, propagate, role, "admin")

    def UpdateGroupLimits(self, group, limits):
        category = self.CategoryGet(group["parent_category"], True)
        # Can't update a group limits with a higher value than its category limits
        if category["limits"] != False:
            for k, v in category["limits"].items():
                if limits and limits.get(k) and v < limits[k]:
                    raise Error(
                        "precondition_required",
                        "Can't update "
                        + group["name"]
                        + " "
                        + k
                        + " limits value with a higher value than its category limits",
                        traceback.format_exc(),
                    )

        with app.app_context():
            r.table("groups").get(group["id"]).update({"limits": limits}).run(db.conn)

    def UpdateSecondaryGroups(self, action, data):
        query = r.table("users").get_all(r.args(data["ids"]))

        if action == "add":
            query = query.update(
                lambda user: {
                    "secondary_groups": user["secondary_groups"].set_union(
                        data["secondary_groups"]
                    )
                }
            )
        elif action == "delete":
            query = query.update(
                lambda user: {
                    "secondary_groups": user["secondary_groups"].difference(
                        data["secondary_groups"]
                    )
                }
            )
        elif action == "overwrite":
            query = query.update({"secondary_groups": data["secondary_groups"]})
        else:
            raise Error("bad_request", "Action: " + action + " not allowed")

        with app.app_context():
            query.run(db.conn)

    def UpdateCategoryLimits(self, category_id, limits, propagate):
        with app.app_context():
            r.table("categories").get(category_id).update({"limits": limits}).run(
                db.conn
            )
        if propagate:
            with app.app_context():
                r.table("groups").get_all(category_id, index="parent_category").update(
                    {"limits": limits}
                ).run(db.conn)

    def WebappDesktops(self, user_id):
        self.Get(user_id)
        with app.app_context():
            desktops = list(
                r.table("domains")
                .get_all(["desktop", user_id], index="kind_user")
                .order_by("name")
                .without("xml", "history_domain", "allowed")
                .run(db.conn)
            )
        return [
            d
            for d in desktops
            if not d.get("tag") or d.get("tag") and d.get("tag_visible")
        ]

    def WebappTemplates(self, user_id):
        with app.app_context():
            templates = list(
                r.table("domains")
                .get_all(["template", user_id], index="kind_user")
                .without("viewer", "xml", "history_domain")
                .run(db.conn)
            )
        return templates

    def groups_users_count(self, groups, user_id):
        query_groups = (
            r.table("users").get_all(r.args(groups), index="group").pluck("id")["id"]
        )
        query_secondary_groups = (
            r.table("users")
            .get_all(r.args(groups), index="secondary_groups")
            .pluck("id")["id"]
        )

        total_groups = (
            list(query_groups.run(db.conn))
            + list(query_secondary_groups.run(db.conn))
            + [user_id]
        )

        with app.app_context():
            return len(list(set(total_groups)))

    def check_secondary_groups_category(self, category, secondary_groups):
        for group in secondary_groups:
            group = self.GroupGet(group)
            if group["parent_category"] != category:
                category = self.CategoryGet(category)["name"]
                raise Error(
                    "forbidden",
                    "Group "
                    + group["name"]
                    + " does not belong to category "
                    + category,
                    traceback.format_exc(),
                )

    def check_group_category(self, data):
        with app.app_context():
            return list(
                r.table("groups")
                .get_all(r.args[data["groups"]], index="id")
                .filter({"parent_category": data["category"]})
                .run(db.conn)
            )

    def change_user_language(self, user_id, lang):
        with app.app_context():
            r.table("users").get(user_id).update({"lang": lang}).run(db.conn)


"""
PASSWORDS MANAGER
"""
import random
import string

import bcrypt


class Password(object):
    def __init__(self):
        None

    def valid(self, plain_password, enc_password):
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), enc_password.encode("utf-8")
        )

    def encrypt(self, plain_password):
        return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

    def generate_human(self, length=6):
        chars = string.ascii_letters + string.digits + "!@#$*"
        rnd = random.SystemRandom()
        return "".join(rnd.choice(chars) for i in range(length))
