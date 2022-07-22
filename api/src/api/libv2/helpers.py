#!/usr/bin/env python
# coding=utf-8
# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

import time

from rethinkdb import RethinkDB

from api import app

r = RethinkDB()
import logging as log

from .flask_rethink import RDB

db = RDB(app)
db.init_app(app)

import random
import string

from ..libv2.isardViewer import isardViewer

isardviewer = isardViewer()

import traceback

from .api_exceptions import Error


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


def _get_reservables(item_type, item_id, tolist=False):
    if item_type == "desktop":
        data = r.table("domains").get(item_id).run(db.conn)
        units = 1
        item_name = data["name"]
    elif item_type == "deployment":
        deployment = r.table("deployments").get(item_id).run(db.conn)
        if not deployment:
            raise Error("not_found", "Deployment id not found")
        item_name = deployment["name"]
        deployment_domains = list(
            r.table("domains").get_all(item_id, index="tag").run(db.conn)
        )
        if not len(deployment_domains):
            ## Now there is no desktop at the deployment. No reservation will be done.
            raise (
                "precondition_required",
                "Deployment has no desktops to be reserved.",
            )
        data = deployment_domains[0]
        units = len(deployment_domains)
    else:
        raise Error("not_found", "Item type " + str(item_type) + " not found")

    if not data["create_dict"].get("reservables") or not any(
        list(data["create_dict"]["reservables"].values())
    ):
        raise Error("precondition_required", "Item has no reservables")
    data = data["create_dict"]["reservables"]
    log.debug("GET RESERVABLES: " + str(data))
    data_without_falses = {k: v for k, v in data.items() if v}
    if tolist:
        return (
            [item for sublist in list(reservables.values()) for item in sublist],
            units,
        )
    return (data_without_falses, units, item_name)


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


def _disk_path(user, parsed_name):
    with app.app_context():
        group_uid = r.table("groups").get(user["group"]).run(db.conn)["uid"]

    dir_path = (
        user["category"]
        + "/"
        + group_uid
        + "/"
        + user["provider"]
        + "/"
        + user["uid"]
        + "-"
        + user["username"]
    )
    filename = parsed_name + ".qcow2"
    return dir_path, filename


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

    # desktop["viewers"] = ["file-spice", "browser-vnc"]
    if desktop["status"] == "Started":
        if (
            "file-rdpgw" in desktop["viewers"]
            or "file-rdpvpn" in desktop["viewers"]
            or "browser-rdp" in desktop["viewers"]
        ):
            if "wireguard" in desktop["create_dict"]["hardware"]["interfaces"]:
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
        },
        **_parse_desktop_booking(desktop),
    }


def _parse_deployment_desktop(desktop, user_id=False):
    visible = desktop.get("tag_visible", False)
    user = desktop["user"]
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
    desktop = _parse_desktop(desktop)
    desktop["viewer"] = viewer
    desktop = {**desktop, **app.internal_users.get(user), **{"visible": visible}}
    desktop["user"] = user
    desktop.pop("type")
    desktop.pop("template")

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

    if not desktop.get("tag"):
        item_id = desktop["id"]
        item_type = "desktop"
    else:
        item_id = desktop.get("tag")
        item_type = "deployment"
    with app.app_context():
        try:
            plan = (
                r.table("bookings")
                .get_all([item_type, item_id], index="item_type-id")
                .filter(lambda plan: plan["end"] > r.now())
                .order_by("start")
                .nth(0)
                .run(db.conn)
            )
        except:
            # log.debug("PLAN IS " + str(len(plan)) + " LENGTH")
            return {
                "needs_booking": True,
                "next_booking_start": None,
                "next_booking_end": None,
                "bookings_id": False,
            }
    return {
        "needs_booking": True,
        "next_booking_start": plan["start"].strftime("%Y-%m-%dT%H:%M%z"),
        "next_booking_end": plan["end"].strftime("%Y-%m-%dT%H:%M%z"),
        "booking_id": desktop.get("booking_id", False),
    }


def _parse_deployment_booking(deployment):
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


# suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
# def humansize(nbytes):
#     i = 0
#     while nbytes >= 1024 and i < len(suffixes)-1:
#         nbytes /= 1024.
#         i += 1
#     f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
#     return '%s %s' % (f, suffixes[i])


def generate_db_media(path_downloaded, filesize):
    parts = path_downloaded.split("/")
    # /isard/media/default/default/local/admin-admin/dsl-4.4.10.iso
    media_id = "_" + parts[-3] + "-" + parts[-5] + "-" + parts[-2] + "-" + parts[-1]
    group_id = parts[-5] + "-" + parts[-4]

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
        )

    with app.app_context():
        username = r.table("users").get(parts[-2])["username"].run(db.conn)
    if username == None:
        raise Error("not_found", "Username not found", traceback.format_exc())

    return {
        "accessed": time.time(),
        "allowed": {
            "categories": False,
            "groups": False,
            "roles": False,
            "users": False,
        },
        "category": parts[-5],
        "description": "Scanned from storage.",
        "detail": "",
        "group": group_id,
        "hypervisors_pools": ["default"],
        "icon": icon,
        "id": media_id,
        "kind": kind,
        "name": parts[-1],
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
        "user": parts[-3]
        + "-"
        + parts[-5]
        + "-"
        + parts[-2],  # "local-default-admin-admin" ,
        "username": username,
    }


def get_user_data(user_id="admin"):
    if user_id == "admin":
        with app.app_context():
            user = list(
                r.table("users")
                .filter({"uid": "admin", "provider": "local"})
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
