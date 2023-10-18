#!/usr/bin/env python
# coding=utf-8
# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3


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


def get_media_domains(storage_id):
    with app.app_context():
        return list(
            r.table("domains")
            .get_all(storage_id, index="media_ids")
            .pluck("id", "kind", "name")
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
