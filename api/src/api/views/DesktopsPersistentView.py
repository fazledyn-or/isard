# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

import json
import logging as log
import os

#!flask/bin/python
# coding=utf-8
import sys
import time
import traceback
from uuid import uuid4

from flask import request
from schema import And, Optional, Schema, SchemaError, Use

from api import app

from ..libv2.api_exceptions import Error
from ..libv2.quotas import Quotas

quotas = Quotas()

from ..libv2.api_desktops_persistent import ApiDesktopsPersistent
from ..libv2.api_hypervisors import get_hypervisors

desktops = ApiDesktopsPersistent()

from ..libv2.api_cards import ApiCards

api_cards = ApiCards()

from .decorators import allowedTemplateId, has_token, is_admin, ownsDomainId


def validate_desktop_schema(desktop_data, validate=True):

    desktop_schema_template = Schema(
        {
            Optional("forced_hyp"): And(Use(list)),
            Optional("options"): {
                Optional("viewers"): {
                    Optional("spice"): {
                        Optional("fullscreen"): And(Use(bool)),
                    }
                }
            },
            Optional("image"): {
                "type": And(Use(str), lambda t: t in ["user", "stock"]),
                Optional("id"): And(Use(str)),
                Optional("file"): {
                    "data": And(Use(str)),
                    "filename": And(Use(str)),
                },
            },
        }
    )
    if validate:
        try:
            desktop_schema_template.validate(desktop_data)
            ## Note: The lambda schema option didn't work
            if desktop_data.get("forced_hyp"):
                hypervisors = get_hypervisors()
                for forced_hyp in desktop_data["forced_hyp"]:
                    if forced_hyp in [hyp["id"] for hyp in hypervisors]:
                        return True
                return False
            return desktop_schema_template.validate(desktop_data)
        except SchemaError:
            return False
    else:
        return desktop_schema_template.json_schema("https://example.com/my-schema.json")


@app.route("/api/v3/desktop/start/<desktop_id>", methods=["GET"])
@has_token
def api_v3_desktop_start(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    user_id = desktops.UserDesktop(desktop_id)
    quotas.DesktopStart(user_id)

    # So now we have checked if desktop exists and if we can create and/or start it
    return (
        json.dumps({"id": desktops.Start(desktop_id)}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktops/start", methods=["PUT"])
@has_token
def api_v3_desktops_start(payload):
    try:
        data = request.get_json(force=True)
        desktops_ids = data["desktops_ids"]
    except:
        Error(
            "bad_request",
            "DesktopS start incorrect body data",
            traceback.traceback.format_exc(),
        )

    for desktop_id in desktops_ids:
        ownsDomainId(payload, desktop_id)
        user_id = desktops.UserDesktop(desktop_id)
        quotas.DesktopStart(user_id)

    # So now we have checked if desktop exists and if we can create and/or start it
    return (
        json.dumps({}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktop/stop/<desktop_id>", methods=["GET"])
@has_token
def api_v3_desktop_stop(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    user_id = desktops.UserDesktop(desktop_id)

    return (
        json.dumps({"id": desktops.Stop(desktop_id)}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktops/stop", methods=["PUT"])
@has_token
def api_v3_desktops_stop(payload, desktop_id):
    try:
        data = request.get_json(force=True)
        desktops_ids = data["desktops_ids"]
    except:
        Error(
            "bad_request",
            "DesktopS start incorrect body data",
            traceback.traceback.format_exc(),
        )
    for desktop_id in desktops_ids:
        ownsDomainId(payload, desktop_id)
        user_id = desktops.UserDesktop(desktop_id)

    return (
        json.dumps({}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/persistent_desktop", methods=["POST"])
@has_token
def api_v3_persistent_desktop_new(payload):
    try:
        desktop_name = request.form.get("desktop_name", type=str)
        desktop_description = request.form.get("desktop_description", type=str)
        template_id = request.form.get("template_id", False)
        forced_hyp = request.form.get("forced_hyp", False)
        user_id = payload["user_id"]
    except:
        raise Error(
            "bad_request",
            "New persistent desktop bad body data",
            traceback.traceback.format_exc(),
        )

    if desktop_name == None or not template_id:
        raise Error(
            "bad_request",
            "New persistent desktop incorrect body data",
            traceback.traceback.format_exc(),
        )

    allowedTemplateId(payload, template_id)
    quotas.DesktopCreate(user_id)

    desktop_id = desktops.NewFromTemplate(
        desktop_name=desktop_name,
        desktop_description=desktop_description,
        template_id=template_id,
        payload=payload,
        forced_hyp=forced_hyp,
    )
    return json.dumps({"id": desktop_id}), 200, {"Content-Type": "application/json"}


@app.route("/api/v3/desktop/from/scratch", methods=["POST"])
@has_token
def api_v3_desktop_from_scratch(payload):
    try:
        name = request.form.get("name", type=str)
        # Optionals but some required (check after)
        if payload["role_id"] == "admin":
            user_id = payload.get("user_id", "local-default-admin-admin")
        else:
            user_id = payload["user_id"]

        ## TODO: If role is manager can create in his category
        ##      If role is teacher can create in his deployment?

        description = request.form.get("description", "")
        disk_user = request.form.get("disk_user", False)
        disk_path = request.form.get("disk_path", False)
        disk_path_selected = request.form.get("disk_path_selected", "/isard/groups")
        disk_bus = request.form.get("disk_bus", "virtio")
        disk_size = request.form.get("disk_size", False)
        disks = request.form.get("disks", False)
        isos = request.form.get("isos", [])
        boot_order = request.form.get("boot_order", ["disk"])
        vcpus = request.form.get("vcpus", 2)
        memory = request.form.get("memory", 4096)
        graphics = request.form.get("graphics", ["default"])
        videos = request.form.get("videos", ["default"])
        interfaces = request.form.get("interfaces", ["default"])
        opsystem = request.form.get("opsystem", ["windows"])
        icon = request.form.get("icon", ["fa-desktop"])
        image = request.form.get("image", "")
        forced_hyp = request.form.get("forced_hyp", False)
        hypervisors_pools = request.form.get("hypervisors_pools", ["default"])
        server = request.form.get("server", False)
        virt_install_id = request.form.get("virt_install_id", False)
        xml = request.form.get("xml", False)

    except:
        raise Error(
            "bad_request",
            "New desktop from scratch bad body data",
            traceback.traceback.format_exc(),
        )

    if name == None:
        raise Error(
            "bad_request",
            "New desktop from scratch bad body data",
            traceback.traceback.format_exc(),
        )

    if not virt_install_id and not xml:
        raise Error(
            "bad_request",
            "New desktop from scratch missing virt_install_id or xml in body data",
            traceback.traceback.format_exc(),
        )

    if not disk_user and not disk_path and not disks:
        raise Error(
            "bad_request",
            "New desktop from scratch missing disk_user or disk_path or disks in body data",
            traceback.traceback.format_exc(),
        )

    if not boot_order not in ["disk", "iso", "pxe"]:
        raise Error(
            "bad_request",
            "New desktop from scratch incorrect boot order in body data",
            traceback.traceback.format_exc(),
        )

    quotas.DesktopCreate(user_id)

    desktop_id = desktops.NewFromScratch(
        name=name,
        user_id=user_id,
        description=description,
        disk_user=disk_user,
        disk_path=disk_path,
        disk_path_selected=disk_path_selected,
        disk_bus=disk_bus,
        disk_size=disk_size,
        disks=disks,
        isos=isos,  # ['_local-default-admin-admin-systemrescue-8.04-amd64.iso']
        boot_order=boot_order,
        vcpus=vcpus,
        memory=memory,
        graphics=graphics,
        videos=videos,
        interfaces=interfaces,
        opsystem=opsystem,
        icon=icon,
        image=image,
        forced_hyp=forced_hyp,
        hypervisors_pools=hypervisors_pools,
        server=server,
        virt_install_id=virt_install_id,
        xml=xml,
    )
    return json.dumps({"id": desktop_id}), 200, {"Content-Type": "application/json"}


@app.route("/api/v3/desktop/<desktop_id>", methods=["PUT"])
@has_token
def api_v3_desktop_edit(payload, desktop_id):
    try:
        data = request.get_json(force=True)
    except:
        Error(
            "bad_request",
            "Desktop edit incorrect body data",
            traceback.traceback.format_exc(),
        )

    if not validate_desktop_schema(data):
        raise Error(
            "bad_request",
            validate_desktop_schema(data, validate=False),
            traceback.traceback.format_exc(),
        )

    ownsDomainId(payload, desktop_id)
    user_id = desktops.UserDesktop(desktop_id)

    ## Pop image from data if exists and process
    if data.get("image"):
        image_data = data.pop("image")

        if not image_data.get("file"):
            img_uuid = api_cards.update(
                desktop_id, image_data["id"], image_data["type"]
            )
            card = api_cards.get_card(img_uuid, image_data["type"])
            return json.dumps(card), 200, {"Content-Type": "application/json"}
        else:
            img_uuid = api_cards.upload(desktop_id, image_data)
            card = api_cards.get_card(img_uuid, image_data["type"])
            return json.dumps(card), 200, {"Content-Type": "application/json"}
    desktops.Update(desktop_id, data)
    return (
        json.dumps(data),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktop/jumperurl/<desktop_id>", methods=["GET"])
@has_token
def api_v3_admin_viewer(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    data = desktops.JumperUrl(desktop_id)
    return (
        json.dumps(data),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/api/v3/desktop/jumperurl_reset/<desktop_id>", methods=["PUT"])
@has_token
def admin_jumperurl_reset(payload, desktop_id):
    ownsDomainId(payload, desktop_id)
    try:
        data = request.get_json()
    except:
        raise Error("bad_request", "Bad body data", traceback.traceback.format_exc())
    response = desktops.JumperUrlReset(desktop_id, disabled=data.get("disabled"))
    return (
        json.dumps(response),
        200,
        {"Content-Type": "application/json"},
    )
