#!/usr/bin/env python
# coding=utf-8
# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

import logging as log
import random
import string
import time
import traceback
import uuid
from datetime import timedelta

from isardvdi_common.api_exceptions import Error
from rethinkdb import RethinkDB

from api import app

from ..libv2.api_allowed import ApiAllowed
from ..libv2.isardViewer import isardViewer
from ..libv2.quotas import Quotas
from ..libv2.validators import check_user_duplicated_domain_name
from ..views.decorators import checkDuplicate, ownsDomainId, ownsMediaId
from .flask_rethink import RDB

r = RethinkDB()
allowed = ApiAllowed()
quotas = Quotas()


db = RDB(app)
db.init_app(app)


isardviewer = isardViewer()


class InternalUsers(object):
    def __init__(self):
        self.users = {}

    def get(self, user_id):
        data = self.users.get(user_id, False)
        if not data:
            with app.app_context():
                try:
                    user = (
                        r.table("users")
                        .get(user_id)
                        .pluck("name", "category", "group")
                        .run(db.conn)
                    )
                    category_name = (
                        r.table("categories")
                        .get(user["category"])
                        .pluck("name")
                        .run(db.conn)["name"]
                    )
                    group_name = (
                        r.table("groups")
                        .get(user["group"])
                        .pluck("name")
                        .run(db.conn)["name"]
                    )
                    self.users[user_id] = {
                        "userName": user["name"],
                        "categoryName": category_name,
                        "groupName": group_name,
                    }
                except:
                    print(traceback.format_exc())
                    return {
                        "userName": "Unknown",
                        "userPhoto": "Unknown",
                        "categoryName": "Unknown",
                        "groupName": "Unknown",
                    }
        return self.users[user_id]

    def list(self):
        return self.users


def _get_reservables(item_type, item_id):
    if item_type == "desktop":
        with app.app_context():
            data = r.table("domains").get(item_id).run(db.conn)
        units = 1
        item_name = data["name"]
    elif item_type == "deployment":
        with app.app_context():
            deployment = r.table("deployments").get(item_id).run(db.conn)
        if not deployment:
            raise Error(
                "not_found",
                "Deployment id not found",
                description_code="not_found",
            )
        item_name = deployment["name"]
        with app.app_context():
            deployment_domains = list(
                r.table("domains").get_all(item_id, index="tag").run(db.conn)
            )
        if not len(deployment_domains):
            # Now there is no desktop at the deployment. No reservation will be done.
            raise (
                "precondition_required",
                "Deployment has no desktops to be reserved.",
            )
        data = deployment_domains[0]
        units = len(deployment_domains)
    else:
        raise Error(
            "not_found",
            "Item type " + str(item_type) + " not found",
            description_code="not_found",
        )

    if not data["create_dict"].get("reservables") or not any(
        list(data["create_dict"]["reservables"].values())
    ):
        raise Error(
            "precondition_required",
            "Item has no reservables",
            description_code="no_reservables",
        )
    data = data["create_dict"]["reservables"]
    data_without_falses = {k: v for k, v in data.items() if v}
    return (data_without_falses, units, item_name)


def _get_domain_reservables(domain_id):
    with app.app_context():
        data = r.table("domains").get(domain_id).run(db.conn)
    if not data["create_dict"].get("reservables") or not any(
        list(data["create_dict"]["reservables"].values())
    ):
        return {"vgpus": []}
    data = data["create_dict"]["reservables"]
    data_without_falses = {k: v for k, v in data.items() if v}
    return data_without_falses


def _parse_string(txt):
    import locale
    import re
    import unicodedata

    if type(txt) is not str:
        txt = txt.decode("utf-8")
    # locale.setlocale(locale.LC_ALL, 'ca_ES')
    prog = re.compile("[-_àèìòùáéíóúñçÀÈÌÒÙÁÉÍÓÚÑÇ .a-zA-Z0-9]+$")
    if not prog.match(txt):
        raise Error(
            "internal_server",
            "Unable to parse string",
            traceback.format_exc(),
            description_code="unable_to_parse_string",
        )
    else:
        # ~ Replace accents
        txt = "".join(
            (
                c
                for c in unicodedata.normalize("NFD", txt)
                if unicodedata.category(c) != "Mn"
            )
        )
        return txt.replace(" ", "_")


def _check(dict, action):
    """
    These are the actions:
    {u'skipped': 0, u'deleted': 1, u'unchanged': 0, u'errors': 0, u'replaced': 0, u'inserted': 0}
    """
    if dict[action] or dict["unchanged"]:
        return True
    if not dict["errors"]:
        return True
    return False


def _random_password(length=16):
    chars = string.ascii_letters + string.digits + "!@#$*"
    rnd = random.SystemRandom()
    return "".join(rnd.choice(chars) for i in range(length))


def _parse_media_info(create_dict):
    medias = ["isos", "floppies", "storage"]
    for m in medias:
        if m in create_dict["hardware"]:
            newlist = []
            for item in create_dict["hardware"][m]:
                with app.app_context():
                    newlist.append(
                        r.table("media")
                        .get(item["id"])
                        .pluck("id", "name", "description")
                        .run(db.conn)
                    )
            create_dict["hardware"][m] = newlist
    return create_dict


def _is_frontend_desktop_status(status):
    frontend_desktop_status = [
        "Creating",
        "CreatingAndStarting",
        "Shutting-down",
        "Stopping",
        "Stopped",
        "Starting",
        "Started",
        "Failed",
        "Downloading",
        "DownloadStarting",
        "Updating",
    ]
    return True if status in frontend_desktop_status else False


def parse_frontend_desktop_status(desktop):
    if (
        desktop["status"].startswith("Creating")
        and desktop["status"] != "CreatingAndStarting"
    ):
        desktop["status"] = "Creating"
    return desktop


def default_guest_properties():
    return {
        "credentials": {
            "username": "isard",
            "password": "pirineus",
        },
        "fullscreen": False,
        "viewers": {
            "file_spice": {"options": None},
            "browser_vnc": {"options": None},
            "file_rdpgw": {"options": None},
            "file_rdpvpn": {"options": None},
            "browser_rdp": {"options": None},
        },
    }


def _parse_desktop(desktop):
    desktop = parse_frontend_desktop_status(desktop)
    desktop["image"] = desktop.get("image", None)
    desktop["from_template"] = desktop.get("parents", [None])[-1]
    if desktop.get("persistent", True):
        desktop["type"] = "persistent"
    else:
        desktop["type"] = "nonpersistent"

    desktop["viewers"] = [
        v.replace("_", "-") for v in list(desktop["guest_properties"]["viewers"].keys())
    ]

    if desktop["status"] == "Started":
        if "wireguard" in [
            i["id"] for i in desktop["create_dict"]["hardware"]["interfaces"]
        ]:
            desktop["ip"] = desktop.get("viewer", {}).get("guest_ip")
            if not desktop["ip"]:
                desktop["status"] = "WaitingIP"
        else:
            desktop["viewers"] = [
                v
                for v in desktop["viewers"]
                if v not in ["file-rdpgw", "file-rdpvpn", "browser-rdp"]
            ]

    if desktop["status"] == "Downloading":
        progress = {
            "percentage": desktop.get("progress", {}).get("received_percent"),
            "throughput_average": desktop.get("progress", {}).get(
                "speed_download_average"
            ),
            "time_left": desktop.get("progress", {}).get("time_left"),
            "size": desktop.get("progress", {}).get("total"),
        }
    else:
        progress = None
    editable = True
    if desktop.get("tag"):
        try:
            with app.app_context():
                deployment_user = (
                    r.table("deployments")
                    .get(desktop.get("tag"))
                    .pluck("user")
                    .run(db.conn)
                )["user"]
            editable = True if deployment_user == desktop["user"] else False
        except:
            log.debug(traceback.format_exc())
            editable = False
    # TODO: Sum all the desktop storages instead of getting only the first one, call get_domain_storage function to retrieve them
    desktop_size = 0
    if desktop.get("type") == "persistent" and desktop["create_dict"]["hardware"].get(
        "disks", [{}]
    )[0].get("storage_id"):
        with app.app_context():
            desktop_storage = (
                r.table("storage")
                .get(desktop["create_dict"]["hardware"]["disks"][0]["storage_id"])
                .pluck({"qemu-img-info": {"actual-size"}})
                .run(db.conn)
            )
        if desktop_storage.get("qemu-img-info"):
            desktop_size = desktop_storage["qemu-img-info"]["actual-size"]
    return {
        **{
            "id": desktop["id"],
            "name": desktop["name"],
            "state": desktop["status"],
            "type": desktop["type"],
            "template": desktop["from_template"],
            "viewers": desktop["viewers"],
            "icon": desktop["icon"],
            "image": desktop["image"],
            "description": desktop["description"],
            "ip": desktop.get("ip"),
            "progress": progress,
            "editable": editable,
            "scheduled": desktop.get("scheduled", {"shutdown": False}),
            "server": desktop.get("server"),
            "accessed": desktop.get("accessed"),
            "desktop_size": desktop_size,
            "tag": desktop.get("tag"),
            "visible": desktop.get("tag_visible"),
            "user": desktop.get("user"),
            "user_name": desktop.get("user_name"),
            "group": desktop.get("group"),
            "group_name": desktop.get("group_name"),
            "category": desktop.get("category"),
            "category_name": desktop.get("category_name"),
            "reservables": desktop["create_dict"].get("reservables"),
            "interfaces": desktop["create_dict"]["hardware"]["interfaces"],
        },
        **_parse_desktop_booking(desktop),
    }


def _parse_deployment_desktop(desktop, user_id=False):
    if desktop["status"] in ["Started", "WaitingIP"] and desktop.get("viewer", {}).get(
        "static"
    ):
        viewer = isardviewer.viewer_data(
            desktop["id"],
            "browser-vnc",
            get_cookie=False,
            get_dict=True,
            domain=desktop,
            user_id=user_id,
        )
    else:
        viewer = False
    user_photo = desktop.get("user_photo")
    desktop = _parse_desktop(desktop)
    desktop["viewer"] = viewer
    desktop["user_photo"] = user_photo

    with app.app_context():
        desktop["user_name"] = (
            r.table("users").get(desktop["user"])["name"].run(db.conn)
        )
        desktop["group_name"] = (
            r.table("groups").get(desktop["group"])["name"].run(db.conn)
        )

    return desktop


def _parse_desktop_booking(desktop):
    if not desktop["create_dict"].get("reservables") or not any(
        list(desktop["create_dict"]["reservables"].values())
    ):
        return {
            "needs_booking": False,
            "next_booking_start": None,
            "next_booking_end": None,
            "booking_id": False,
        }
    item_id = desktop["id"]
    item_type = "desktop"
    with app.app_context():
        booking = (
            r.table("bookings")
            .get_all([item_type, item_id], index="item_type-id")
            .filter(lambda b: b["end"] > r.now())
            .order_by("start")
            .run(db.conn)
        )
        if not booking and desktop.get("tag"):
            booking = (
                r.table("bookings")
                .get_all(["deployment", desktop.get("tag")], index="item_type-id")
                .filter(lambda b: b["end"] > r.now())
                .order_by("start")
                .run(db.conn)
            )

    if booking:
        return {
            "needs_booking": True,
            "next_booking_start": booking[0]["start"].strftime("%Y-%m-%dT%H:%M%z"),
            "next_booking_end": booking[0]["end"].strftime("%Y-%m-%dT%H:%M%z"),
            "booking_id": desktop.get("booking_id", False),
        }
    else:
        return {
            "needs_booking": True,
            "next_booking_start": None,
            "next_booking_end": None,
            "booking_id": False,
        }


def set_current_booking(desktop):
    if not desktop["create_dict"].get("reservables") or not any(
        list(desktop["create_dict"]["reservables"].values())
    ):
        return
    item_id = desktop["id"]
    item_type = "desktop"
    with app.app_context():
        booking = (
            r.table("bookings")
            .get_all([item_type, item_id], index="item_type-id")
            .filter(lambda b: b["start"] < r.now() & b["end"] > r.now())
            .order_by("start")
            .run(db.conn)
        )
        if not booking and desktop.get("tag"):
            booking = (
                r.table("bookings")
                .get_all(["deployment", desktop.get("tag")], index="item_type-id")
                .filter(lambda b: b["start"] < r.now() & b["end"] > r.now())
                .order_by("start")
                .run(db.conn)
            )

    if booking:
        with app.app_context():
            r.table("domains").get(desktop["id"]).update(
                {"booking_id": booking[0]["id"]}
            ).run(db.conn)
    return


def _parse_deployment_booking(deployment):
    with app.app_context():
        deployment_domains = list(
            r.table("domains").get_all(deployment["id"], index="tag").run(db.conn)
        )
    if not len(deployment_domains):
        return {
            "needs_booking": False,
            "next_booking_start": None,
            "next_booking_end": None,
            "booking_id": False,
        }
    desktop = deployment_domains[0]
    return _parse_desktop_booking(desktop)


def parse_domain_insert(new_data):
    if new_data.get("hardware", {}).get("reservables", {}).get("vgpus") == ["None"]:
        new_data["hardware"]["reservables"]["vgpus"] = None

    interfaces = new_data.get("hardware", {}).get("interfaces", [])
    new_data["hardware"]["interfaces"] = []
    for interface in interfaces:
        new_data["hardware"]["interfaces"].append(
            {"id": interface, "mac": gen_new_mac()}
        )
    return new_data


def parse_domain_update(domain_id, new_data, admin_or_manager=False):
    with app.app_context():
        domain = r.table("domains").get(domain_id).run(db.conn)
    if not domain:
        raise Error(
            "not_found",
            "Not found domain to be updated",
            traceback.format_exc(),
            description="not_found",
        )
    new_domain = {}

    if admin_or_manager:
        if "forced_hyp" in new_data and new_data.get("forced_hyp") != domain.get(
            "forced_hyp"
        ):
            new_domain["forced_hyp"] = new_data.get("forced_hyp")
        if "favourite_hyp" in new_data and new_data.get("favourite_hyp") != domain.get(
            "favourite_hyp"
        ):
            new_domain["favourite_hyp"] = new_data.get("favourite_hyp")
        if "server" in new_data and new_data.get("server") != domain.get("server"):
            new_domain = {
                **new_domain,
                **{
                    "server": new_data.get("server"),
                },
            }
        if "xml" in new_data and new_data.get("xml") != domain.get("xml"):
            new_domain = {
                **new_domain,
                **{"status": "Updating", "xml": new_data["xml"]},
            }

    if "name" in new_data and new_data.get("name") != domain.get("name"):
        new_domain["name"] = new_data.get("name")
    if "description" in new_data and new_data.get("description") != domain.get(
        "description"
    ):
        new_domain["description"] = new_data.get("description")

    if new_data.get("guest_properties") and new_data.get(
        "guest_properties"
    ) != domain.get("guest_properties"):
        new_domain["guest_properties"] = {
            **new_data["guest_properties"],
            **{"viewers": r.literal(new_data["guest_properties"].pop("viewers"))},
        }

    if new_data.get("hardware") and new_data.get("hardware") != domain.get("hardware"):
        if new_data["hardware"].get("virtualization_nested"):
            new_data["hardware"]["virtualization_nested"] = new_data["hardware"][
                "virtualization_nested"
            ]
        if new_data["hardware"].get("memory"):
            new_data["hardware"]["memory"] = int(
                new_data["hardware"]["memory"] * 1048576
            )
        if new_data["hardware"].get("disk_bus"):
            disk_bus = (
                new_data["hardware"]["disk_bus"]
                if new_data["hardware"]["disk_bus"] != "default"
                else "virtio"
            )
            new_data["hardware"] = {
                **new_data["hardware"],
                **{
                    "disks": [
                        {
                            **domain["create_dict"]["hardware"]["disks"][0],
                            **{"bus": disk_bus},
                        }
                    ]
                },
            }

        if new_data["hardware"].get("interfaces"):
            old_interfaces = [
                interface["id"]
                for interface in domain["create_dict"]["hardware"]["interfaces"]
            ]
            new_interfaces = new_data["hardware"].get("interfaces")
            if old_interfaces != new_interfaces:
                interfaces = []
                for new_interface in new_interfaces:
                    interfaces.append(
                        {
                            "id": new_interface,
                            "mac": next(
                                (
                                    item["mac"]
                                    for item in domain["create_dict"]["hardware"][
                                        "interfaces"
                                    ]
                                    if item["id"] == new_interface
                                ),
                                gen_new_mac(),
                            ),
                        }
                    )
                new_data["hardware"] = {
                    **new_data["hardware"],
                    **{"interfaces": r.literal(interfaces)},
                }
            else:
                new_data["hardware"].pop("interfaces", None)

        if new_data["hardware"].get("reservables"):
            if new_data["hardware"]["reservables"].get("vgpus") == ["None"]:
                new_data["hardware"]["reservables"]["vgpus"] = None
            new_domain = {
                **new_domain,
                **{
                    "status": "Updating",
                    "create_dict": {
                        "hardware": new_data["hardware"],
                        "reservables": r.literal(
                            new_data["hardware"].pop("reservables")
                        ),
                    },
                },
            }
        else:
            new_domain = {
                **new_domain,
                **{
                    "create_dict": {"hardware": new_data["hardware"]},
                },
            }
    return new_domain


def generate_db_media(path_downloaded, filesize):
    media_id = str(uuid.uuid4())
    admin_data = get_user_data()

    icon = False
    if path_downloaded.split(".")[-1] == "iso":
        icon = "fa-circle-o"
        kind = "iso"
    if path_downloaded.split(".")[-1] == "fd":
        icon = "fa-floppy-o"
        kind = "floppy"
    if path_downloaded.split(".")[-1].startswith("qcow"):
        icon = "fa-hdd-o"
        kind = path_downloaded.split(".")[-1]
    if not icon:
        raise Error(
            "precondition_required",
            "Skipping uploaded file as has unknown extension",
            traceback.format_exc(),
            description_code="unknown_extension",
        )

    with app.app_context():
        username = r.table("users").get(parts[-2])["username"].run(db.conn)
    if username == None:
        raise Error(
            "not_found",
            "Username not found",
            traceback.format_exc(),
            description_code="not_found",
        )

    return {
        "accessed": int(time.time()),
        "allowed": {
            "categories": False,
            "groups": False,
            "roles": False,
            "users": False,
        },
        "category": admin_data["category"],
        "description": "Scanned from storage.",
        "detail": "",
        "group": admin_data["group"],
        "hypervisors_pools": ["default"],
        "icon": icon,
        "id": media_id,
        "kind": kind,
        "name": path_downloaded.split("/")[-1],
        "path": "/".join(
            path_downloaded.rsplit("/", 6)[2:]
        ),  # "default/default/local/admin-admin/dsl-4.4.10.iso" ,
        "path_downloaded": path_downloaded,
        "progress": {
            "received": filesize,
            "received_percent": 100,
            "speed_current": "10M",
            "speed_download_average": "10M",
            "speed_upload_average": "0",
            "time_left": "--:--:--",
            "time_spent": "0:00:05",
            "time_total": "0:00:05",
            "total": filesize,
            "total_percent": 100,
            "xferd": "0",
            "xferd_percent": "0",
        },
        "status": "Downloaded",
        "url-isard": False,
        "url-web": False,
        "user": admin_data["user"],  # "local-default-admin-admin" ,
        "username": admin_data["username"],
    }


def get_user_data(user_id="admin"):
    if user_id == "admin":
        with app.app_context():
            user = list(
                r.table("users")
                .get_all("admin", index="uid")
                .filter({"provider": "local"})
                .run(db.conn)
            )[0]
    else:
        with app.app_context():
            user = r.table("users").get(user_id).run(db.conn)
    return {
        "category": user["category"],
        "group": user["group"],
        "user": user["id"],
        "username": user["username"],
    }


def gen_payload_from_user(user_id):
    with app.app_context():
        user = (
            r.table("users")
            .get(user_id)
            .merge(
                lambda d: {
                    "category_name": r.table("categories").get(d["category"])["name"],
                    "group_name": r.table("groups").get(d["group"])["name"],
                    "role_name": r.table("roles").get(d["role"])["name"],
                }
            )
            .without("password")
            .run(db.conn)
        )
    return {
        "provider": user["provider"],
        "user_id": user["id"],
        "name": user["name"],
        "uid": user["uid"],
        "username": user["username"],
        "photo": user.get("photo", ""),
        "role_id": user["role"],
        "role_name": user["role_name"],
        "category_id": user["category"],
        "category_name": user["category_name"],
        "group_id": user["group"],
        "group_name": user["group_name"],
    }


def gen_random_mac():
    mac = [
        0x52,
        0x54,
        0x00,
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
    ]
    return ":".join(map(lambda x: "%02x" % x, mac))


def gen_new_mac():
    with app.app_context():
        all_macs = list(
            r.table("domains")
            .get_all("desktop", index="kind")
            .pluck({"create_dict": {"hardware": {"interfaces": True}}})["create_dict"][
                "hardware"
            ]["interfaces"]
            .concat_map(lambda x: x["mac"])
            .run(db.conn)
        )
    new_mac = gen_random_mac()
    # 24 bit combinations = 16777216 ~= 16.7 million. Is this enough macs for your system?
    # Take into account that each desktop could have múltime interfaces... still milions of unique macs
    while all_macs.count(new_mac) > 0:
        new_mac = gen_random_mac()
    return new_mac


def change_owner_desktop(user_id, desktop_id):
    data = change_owner_domain_data(desktop_id, user_id)
    desktop_data = data["domain_data"]
    user_data = data["user_data"]

    # check if it's associated with a deployment
    if desktop_data.get("tag"):
        raise Error(
            "forbidden",
            "Changing ownership is not permitted for deployed desktops.",
        )
    quotas.desktop_create(user_data["new_user"]["user"])

    change_storage_ownership(desktop_data, user_id)
    revoke_hardware_permissions(desktop_data, user_data["payload"])

    with app.app_context():
        if not _check(
            r.table("domains")
            .get(desktop_id)
            .update(user_data["new_user"], return_changes=True)
            .run(db.conn),
            "replaced",
        ):
            raise Error("bad_request", "No new owner data provided")


def change_owner_template(user_id, template_id):
    data = change_owner_domain_data(template_id, user_id)
    template_data = data["domain_data"]
    user_data = data["user_data"]

    if user_data["payload"]["role_id"] == "user":
        raise Error("forbidden", 'Role "user" can not own templates')
    quotas.template_create(user_data["new_user"]["user"])

    change_storage_ownership(template_data, user_id)
    revoke_hardware_permissions(template_data, user_data["payload"])

    with app.app_context():
        if not _check(
            r.table("domains")
            .get(template_id)
            .update(user_data["new_user"], return_changes=True)
            .run(db.conn),
            "replaced",
        ):
            raise Error("bad_request", "No new owner data provided")


def change_owner_media(user_id, media_id):
    user_data = get_new_user_data(user_id)

    with app.app_context():
        media_data = (
            r.table("media").get(media_id).pluck("category", "name").run(db.conn)
        )

    ## if new owner is from another category, delete
    # permissions of groups and users of old category
    if user_data["new_user"]["category"] is not media_data["category"]:
        user_data["new_user"]["allowed"] = {
            "categories": False,
            "groups": False,
            "users": False,
        }

    quotas.media_create(user_data["new_user"]["user"])
    checkDuplicate("media", media_data["name"], user=user_data["new_user"]["user"])

    with app.app_context():
        if not _check(
            r.table("media")
            .get(media_id)
            .update(user_data["new_user"], return_changes=True)
            .run(db.conn),
            "replaced",
        ):
            raise Error("bad_request", "No new owner data provided")


def get_new_user_data(user_id):
    with app.app_context():
        user = (
            r.table("users")
            .get(user_id)
            .pluck("username", "category", "group", "role", "id")
            .run(db.conn)
        )
    new_user = {
        "username": user["username"],
        "category": user["category"],
        "group": user["group"],
        "user": user_id,
    }

    payload = {
        "role_id": user["role"],
        "category_id": user["category"],
        "user_id": user["id"],
        "group_id": user["group"],
    }

    return {"new_user": new_user, "payload": payload}


def change_storage_ownership(domain_data, user_id):
    storage_ids = []
    for disk in domain_data["create_dict"]["hardware"]["disks"]:
        if disk.get("storage_id"):
            storage_ids.append(disk["storage_id"])
    with app.app_context():
        r.table("storage").get_all(*storage_ids).update({"user_id": user_id}).run(
            db.conn
        )
        r.table("domains").get(domain_data["id"]).update(
            {"create_dict": domain_data["create_dict"]}
        ).run(db.conn)


def revoke_hardware_permissions(domain_data, payload):
    domain_data["create_dict"]["hardware"]["memory"] = (
        domain_data["create_dict"]["hardware"]["memory"] / 1024 / 1024
    )

    quotas.limit_user_hardware_allowed(payload, domain_data["create_dict"])

    domain_data["create_dict"]["hardware"]["memory"] = (
        domain_data["create_dict"]["hardware"]["memory"] * 1024 * 1024
    )


def change_owner_domain_data(domain_id, user_id):
    user_data = get_new_user_data(user_id)

    with app.app_context():
        domain_data = (
            r.table("domains")
            .get(domain_id)
            .pluck("create_dict", "kind", "tag", "name", "id", "category", "name")
            .run(db.conn)
        )

    ## if new owner is from another category, delete
    # permissions of groups and users of old category
    if user_data["new_user"]["category"] is domain_data["category"]:
        user_data["new_user"]["allowed"] = {
            "categories": False,
            "groups": False,
            "users": False,
        }

    ## check if domain name is duplicated
    check_user_duplicated_domain_name(
        domain_data["name"], user_data["payload"]["user_id"]
    )

    return {"user_data": user_data, "domain_data": domain_data}


# This has no recursion. Call GetTemplateTreeList
def TemplateTreeList(template_id):
    # Get derivated from this template (and derivated from itself)
    derivated = _derivated(template_id)

    # Duplicated templates should have the same parent as the original
    # Except for duplicates from root template
    duplicated = _duplicated(template_id)

    derivated = list(derivated) + list(duplicated)

    domains = []
    for d in derivated:
        domains.append(
            {
                "id": d["id"],
                "parent": d["parents"][-1]
                if d.get("parents")
                else d["duplicate_parent_template"],
                "name": d["name"],
                "kind": d["kind"],
                "user": d["user"],
                "category": d["category"],
                "group": d["group"],
                "username": d["username"],
                "user_name": d["user_name"],
            }
        )
    return domains


# This is the function to be called
def GetAllTemplateDerivates(template_id, user_id=None):
    levels = {}
    derivated = TemplateTreeList(template_id)
    with app.app_context():
        template = (
            r.table("domains")
            .get(template_id)
            .pluck("user", "name", "category", "group")
            .merge(
                lambda d: {
                    "username": r.table("users").get(d["user"])["username"],
                    "user_name": r.table("users").get(d["user"])["name"],
                }
            )
            .run(db.conn)
        )
    for n in derivated:
        levels.setdefault(n["parent"], []).append(n)
    recursion = TemplateTreeRecursion(template_id, levels)
    all_domains_id = [
        {
            "id": template_id,
            "name": template["name"],
            "kind": "template",
            "user": template["user"],
            "category": template["category"],
            "group": template["group"],
            "username": template["username"],
            "user_name": template["user_name"],
        }
    ]
    if user_id:
        with app.app_context():
            user = (
                r.table("users")
                .get(user_id)
                .pluck("id", "category", "role")
                .run(db.conn)
            )
    for t in recursion:
        if not user_id or (
            (user["role"] == "admin")
            or (user["role"] == "manager" and t["category"] == user["category"])
            or (user["role"] == "advanced" and t["user"] == user["id"])
        ):
            all_domains_id.append(
                {
                    "id": t["id"],
                    "name": t["name"],
                    "kind": t["kind"],
                    "user": t["user"],
                    "category": t["category"],
                    "group": t["group"],
                    "username": t["username"],
                    "user_name": t["user_name"],
                }
            )
        else:
            raise Error(
                "forbidden",
                "This template has derivatives not owned by your category",
                traceback.format_exc(),
            )
    return all_domains_id


# Call GetTemplateTreeList. This is a subfunction only.
def TemplateTreeRecursion(template_id, levels):
    nodes = [dict(n) for n in levels.get(template_id, [])]
    for n in nodes:
        children = TemplateTreeRecursion(n["id"], levels)
        if children:
            n["children"] = children
    return nodes


def _derivated(template_id):
    with app.app_context():
        return list(
            r.db("isard")
            .table("domains")
            .get_all(template_id, index="parents")
            .pluck(
                "id",
                "name",
                "parents",
                "duplicate_parent_template",
                "user",
                "group",
                "category",
                "kind",
            )
            .merge(
                lambda d: {
                    "username": r.table("users").get(d["user"])["username"],
                    "user_name": r.table("users").get(d["user"])["name"],
                }
            )
            .run(db.conn)
        )


def _duplicated(template_id):
    with app.app_context():
        duplicated_from_original = list(
            r.table("domains")
            .get_all(template_id, index="duplicate_parent_template")
            .pluck(
                "id",
                "name",
                "parents",
                "duplicate_parent_template",
                "user",
                "group",
                "category",
                "kind",
            )
            .merge(
                lambda d: {
                    "username": r.table("users").get(d["user"])["username"],
                    "user_name": r.table("users").get(d["user"])["name"],
                }
            )
            .run(db.conn)
        )

    # Recursively get templates derived from duplicated templates
    derivated_from_duplicated = []
    for d in duplicated_from_original:
        derivated_from_duplicated += _derivated(d["id"])
    return duplicated_from_original + derivated_from_duplicated


def wait_status(
    desktops_ids, current_status, wait_seconds=0, interval_seconds=2, raise_exc=False
):
    desktops_status = list(
        r.table("domains")
        .get_all(r.args(desktops_ids))
        .pluck("status")["status"]
        .run(db.conn)
    )
    if wait_seconds == 0:
        return desktops_status
    seconds = 0
    while current_status in desktops_status and seconds <= wait_seconds:
        time.sleep(interval_seconds)
        seconds += interval_seconds
        with app.app_context():
            try:
                desktops_status = list(
                    r.table("domains")
                    .get_all(r.args(desktops_ids))
                    .pluck("status")["status"]
                    .run(db.conn)
                )
            except:
                raise Error(
                    "not_found",
                    "Desktop not found",
                    traceback.format_exc(),
                    description_code="not_found",
                )
    if current_status in desktops_status:
        if raise_exc:
            raise Error(
                "internal_server",
                "Engine could not change "
                + desktops_ids
                + " status from "
                + current_status
                + " in "
                + str(wait_seconds),
                traceback.format_exc(),
                description_code="generic_error",
            )
        else:
            return False
    return desktops_status


def desktops_stop(desktops_ids, wait_seconds=30):
    with app.app_context():
        r.table("domains").get_all(r.args(desktops_ids), index="id").filter(
            {"status": "Shutting-down"}
        ).update({"status": "Stopping", "accessed": int(time.time())}).run(db.conn)
        r.table("domains").get_all(r.args(desktops_ids), index="id").filter(
            {"status": "Started"}
        ).update({"status": "Stopping", "accessed": int(time.time())}).run(db.conn)
    return wait_status(
        desktops_ids, current_status="Stopping", wait_seconds=wait_seconds
    )
