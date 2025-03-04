#!/usr/bin/env python
# coding=utf-8
# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3


import time

from isardvdi_common.api_exceptions import Error
from rethinkdb import RethinkDB

from api import app

r = RethinkDB()
import csv
import io
import traceback

from .flask_rethink import RDB

db = RDB(app)
db.init_app(app)

import logging as log

from isardvdi_common.api_exceptions import Error


def get_disks_ids_by_status(status=None):
    query = r.table("storage")
    if status:
        if status == "other":
            query = query.filter(
                lambda disk: r.expr(["ready", "deleted"])
                .contains(disk["status"])
                .not_()
            )
        else:
            query = query.get_all(status, index="status")

    with app.app_context():
        return list(query.pluck("id")["id"].run(db.conn))


def get_disks(user_id=None, status=None, pluck=None, category_id=None):
    query = r.table("storage")
    if user_id:
        query = query.get_all(user_id, index="user_id")
        if status:
            query = query.filter({"status": status})
    elif status:
        if status == "other":
            # get status not in ready or deleted
            query = query.filter(
                lambda disk: r.expr(["ready", "deleted"])
                .contains(disk["status"])
                .not_()
            )
        else:
            query = query.get_all(status, index="status")

    if pluck:
        query = query.pluck(pluck)
    else:
        query = query.pluck(
            [
                "id",
                "type",
                "status",
                "directory_path",
                "parent",
                "user_id",
                "status_logs",
                "task",
                {"qemu-img-info": {"virtual-size": True, "actual-size": True}},
            ]
        )
    if status != "deleted":
        if user_id:
            query = query.merge(
                lambda disk: {
                    "user_name": r.table("users")
                    .get(disk["user_id"])
                    .default({"name": "[DELETED] " + disk["user_id"]})["name"],
                    "category": r.table("users")
                    .get(disk["user_id"])
                    .default({"category": "[DELETED]"})["category"],
                    "domains": r.table("domains")
                    .get_all(disk["id"], index="storage_ids")
                    .filter({"user": user_id})
                    .count(),
                }
            )
        else:
            query = query.merge(
                lambda disk: {
                    "user_name": r.table("users")
                    .get(disk["user_id"])
                    .default({"name": "[DELETED] " + disk["user_id"]})["name"],
                    "category": r.table("users")
                    .get(disk["user_id"])
                    .default({"category": "[DELETED]"})["category"],
                    "domains": r.table("domains")
                    .get_all(disk["id"], index="storage_ids")
                    .count(),
                }
            )
    else:
        query = query.merge(
            lambda disk: {
                "user_name": r.table("users")
                .get(disk["user_id"])
                .default({"name": "[DELETED] " + disk["user_id"]})["name"],
                "category": r.table("users")
                .get(disk["user_id"])
                .default({"category": "[DELETED]"})["category"],
                "domains": r.table("domains")
                .get_all(disk["id"], index="storage_ids")
                .count(),
            }
        )

    if category_id:
        query = query.filter({"category": category_id})

    with app.app_context():
        return list(query.run(db.conn))


def get_user_ready_disks(user_id):
    query = (
        r.table("storage")
        .get_all([user_id, "ready"], index="user_status")
        .pluck(
            [
                "id",
                "user_id",
                "user_name",
                {"qemu-img-info": {"virtual-size": True, "actual-size": True}},
                "status_logs",
            ],
        )
        .merge(
            lambda disk: {
                "user_name": r.table("users")
                .get(disk["user_id"])
                .default({"name": "[DELETED] " + disk["user_id"]})["name"],
                "category": r.table("users")
                .get(disk["user_id"])
                .default({"category": "[DELETED]"})["category"],
                "domains": r.table("domains")
                .get_all(disk["id"], index="storage_ids")
                .filter({"user": user_id})
                .pluck("id", "name")
                .coerce_to("array"),
            }
        )
    )

    with app.app_context():
        return list(query.run(db.conn))


def get_storage_domains(storage_id):
    with app.app_context():
        return list(
            r.table("domains")
            .get_all(storage_id, index="storage_ids")
            .pluck("id", "kind", "name")
            .run(db.conn)
        )


def get_domain_storage(domain_id):
    with app.app_context():
        r.table("domains").get(domain_id).pluck(
            {"create_dict": {"hardware": {"disks": {"storage_id": True}}}}
        ).eq_join().run(db.conn)


def get_media_domains(media_ids):
    with app.app_context():
        return list(
            r.table("domains")
            .get_all(media_ids, index="media_ids")
            .eq_join("user", r.table("users"))
            .pluck(
                {
                    "left": {
                        "name": True,
                        "kind": True,
                        "id": True,
                        "user": True,
                    },
                    "right": {
                        "id": True,
                        "group": True,
                        "category": True,
                        "role": True,
                    },
                }
            )
            .map(
                lambda doc: {
                    "id": doc["left"]["id"],
                    "name": doc["left"]["name"],
                    "kind": doc["left"]["kind"],
                    "user": doc["left"]["user"],
                    "user_data": {
                        "role_id": doc["right"]["role"],
                        "category_id": doc["right"]["category"],
                        "group_id": doc["right"]["group"],
                        "user_id": doc["right"]["id"],
                    },
                }
            )
            .run(db.conn)
        )


def parse_disks(disks):
    parsed_disks = []
    for disk in disks:
        if disk.get("qemu-img-info"):
            disk["actual_size"] = disk["qemu-img-info"]["actual-size"]
            disk["virtual_size"] = disk["qemu-img-info"]["virtual-size"]
            disk["last"] = disk["status_logs"][-1]["time"]

            disk.pop("qemu-img-info")
            disk.pop("status_logs")
            parsed_disks.append(disk)
    return parsed_disks


def get_disk_tree():
    root = {"id": None}
    query = (
        r.table("storage")
        .merge(
            lambda disk: {
                "user_name": r.table("users")
                .get(disk["user_id"])["name"]
                .default("[DELETED]"),
                "category_name": r.table("categories")
                .get(r.table("users").get(disk["user_id"])["category"])["name"]
                .default("[DELETED]"),
                "title": disk["id"],
                "icon": "fa fa-folder-open",
                "domains": r.table("domains")
                .get_all(disk["id"], index="storage_ids")
                .count(),
            }
        )
        .pluck(
            "id",
            "parent",
            "status",
            "directory_path",
            "user_name",
            "category_name",
            "domains",
            "title",
            "icon",
        )
        .run(db.conn)
    )

    def recursive(query, parent):
        parent["children"] = []
        for item in query:
            if item.get("parent") == parent["id"]:
                parent["children"].append(item)
                recursive(query, item)

    recursive(list(query), root)
    return root["children"]


def get_domains_delete_pending(category_id=None):
    query = r.table("storage").get_all("delete_pending", index="status")
    if category_id:
        query = query.filter({"last_domain_attached": {"category": category_id}})
    query = query.pluck(
        "id",
        "type",
        "status",
        "directory_path",
        "parent",
        "user_id",
        "status_logs",
        "last_domain_attached",
        {"qemu-img-info": {"virtual-size": True, "actual-size": True}},
    )
    query = query.merge(
        lambda disk: {
            "user_name": r.table("users").get(disk["user_id"])["name"],
            "category_name": r.table("categories").get(
                r.table("users").get(disk["user_id"])["category"]
            )["name"],
        }
    )
    with app.app_context():
        return list(query.run(db.conn))


def delete_storage(storage_id):
    with app.app_context():
        if not _check(
            r.table("storage")
            .get(storage_id)
            .update({"status": "Deleting"})
            .run(db.conn),
            "replaced",
        ):
            raise Error(
                "internal_server",
                "Internal server error",
                traceback.format_exc(),
                description_code="generic_error",
            )


def restore_disk(storage_id, restore_desktops=True):
    update = {
        "status": "ready",
        "status_logs": r.row["status_logs"].append(
            {"time": int(time.time()), "status": "ready"}
        ),
    }
    if restore_desktops:
        update["last_domain_attached"] = None
    try:
        with app.app_context():
            if restore_desktops:
                r.table("domains").insert(
                    r.table("storage").get(storage_id)["last_domain_attached"]
                ).run(db.conn)

            r.table("storage").get(storage_id).update(update).run(db.conn)
    except:
        raise Error(
            "internal_server",
            "Internal server error",
            traceback.format_exc(),
            description_code="generic_error",
        )


def _add_storage_log(storage_id, status):
    with app.app_context():
        r.table("storage").get(storage_id).update(
            {
                "status_logs": r.row["status_logs"].append(
                    {"time": int(time.time()), "status": status}
                ),
            }
        ).run(db.conn)
