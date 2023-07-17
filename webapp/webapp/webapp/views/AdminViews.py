# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

import json
import logging as log

from flask import flash, jsonify, make_response, redirect, render_template, request
from flask_login import current_user, login_required, login_user, logout_user

from webapp import app

from ..auth.authentication import *
from ..lib.admin_api import get_login_path, upload_backup
from ..lib.log import *
from .decorators import isAdmin, isAdminManager, maintenance

monitor_host = os.getenv("GRAFANA_WEBAPP_URL")
if not monitor_host:
    monitor_host = f'https://{os.getenv("DOMAIN", "localhost")}/monitor'


@app.route("/isard-admin/admin/landing", methods=["GET"])
@login_required
@maintenance
def admin_landing():
    if current_user.is_admin:
        return render_template(
            "admin/pages/hypervisors.html",
            title="Hypervisors",
            header="Hypervisors",
            nav="Hypervisors",
            monitor_host=monitor_host,
        )
    if current_user.role == "manager":
        return render_template(
            "admin/pages/desktops.html",
            title="Desktops",
            nav="Desktops",
            icon="desktops",
            monitor_host=monitor_host,
        )


@app.route("/isard-admin/about", methods=["GET"])
@maintenance
def about():
    return render_template(
        "pages/about.html",
        title="About",
        header="About",
        nav="About",
        monitor_host=monitor_host,
    )


@app.route("/isard-admin/healthcheck", methods=["GET"])
def healthcheck():
    return ""


"""
LOGIN PAGE
"""


@app.route("/isard-admin/login", methods=["POST", "GET"])
@app.route("/isard-admin/login/<category>", methods=["POST", "GET"])
def login(category="default"):
    user = get_authenticated_user()
    if user:
        login_user(user)
        flash("Authenticated via backend.", "success")
        return render_template(
            "admin/pages/desktops.html",
            title="Desktops",
            nav="Desktops",
            icon="desktops",
            monitor_host=monitor_host,
        )
    return redirect("/login")


@app.route("/isard-admin/logout/remote")
def remote_logout():
    try:
        logout_ram_user(current_user.id)
    except:
        # The user does not exist already
        None
    logout_user()
    return jsonify(success=True)


@app.route("/isard-admin/logout")
@login_required
def logout():
    login_path = get_login_path()
    response = make_response(
        f"""
            <!DOCTYPE html>
            <html>
                <body>
                    <script>
                        localStorage.removeItem('token');
                        window.location = '{login_path}';
                    </script>
                </body>
            </html>
        """
    )
    remote_logout()
    return response


"""
LANDING ADMIN PAGE
"""


@app.route("/isard-admin/admin")
@login_required
@isAdmin
def admin():
    return render_template(
        "admin/pages/hypervisors.html",
        title="Hypervisors",
        header="Hypervisors",
        nav="Hypervisors",
        monitor_host=monitor_host,
    )


"""
DOMAINS PAGES
"""


@app.route("/isard-admin/admin/domains/render/<nav>")
@login_required
@isAdminManager
def admin_domains(nav="Domains"):
    icon = ""
    if nav == "Desktops":
        icon = "desktop"
        return render_template(
            "admin/pages/desktops.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    if nav == "Templates":
        icon = "cubes"
        return render_template(
            "admin/pages/templates.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    if nav == "Deployments":
        icon = "tv"
        return render_template(
            "admin/pages/deployments.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    if nav == "Storage":
        icon = "folder-open"
        return render_template(
            "admin/pages/storage.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    if nav == "Bases":
        icon = "cubes"
    if nav == "Resources":
        icon = "arrows-alt"
        return render_template(
            "admin/pages/domains_resources.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    if nav == "Bookables":
        icon = "briefcase"
        return render_template(
            "admin/pages/bookables.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    if nav == "BookablesEvents":
        icon = "history"
        return render_template(
            "admin/pages/bookables_events.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    if nav == "Priority":
        icon = "briefcase"
        return render_template(
            "admin/pages/bookables_priority.html",
            title=nav,
            nav=nav,
            icon=icon,
            monitor_host=monitor_host,
        )
    return render_template(
        "admin/pages/desktops.html",
        title=nav,
        nav=nav,
        icon=icon,
        monitor_host=monitor_host,
    )


"""
MEDIA
"""


@app.route("/isard-admin/admin/isard-admin/media", methods=["POST", "GET"])
@login_required
@isAdminManager
def admin_media():
    return render_template(
        "admin/pages/media.html",
        nav="Media",
        title="Media",
        monitor_host=monitor_host,
    )


"""
USERS
"""


@app.route("/isard-admin/admin/users/<nav>", methods=["POST", "GET"])
@login_required
@isAdminManager
def admin_users(nav):
    if nav == "Management":
        return render_template(
            "admin/pages/users_management.html",
            nav=nav,
            title="Management",
            monitor_host=monitor_host,
        )
    elif nav == "QuotasLimits":
        return render_template(
            "admin/pages/users_quotas_limits.html",
            nav=nav,
            title="Quotas / Limits",
            monitor_host=monitor_host,
        )


@app.route("/isard-admin/admin/users/UserStorage", methods=["POST", "GET"])
@login_required
@isAdmin
def admin_users_user_storage():
    return render_template(
        "admin/pages/user_storage.html",
        nav="UserStorage",
        title="User Storage",
        monitor_host=monitor_host,
    )


"""
USAGE
"""


@app.route("/isard-admin/admin/usage", methods=["GET"])
@login_required
@isAdminManager
def admin_usage():
    return render_template(
        "admin/pages/usage.html",
        nav="Usage",
        title="Usage",
        monitor_host=monitor_host,
    )


@app.route("/isard-admin/admin/usage_config", methods=["GET"])
@login_required
@isAdminManager
def admin_usage_config():
    return render_template(
        "admin/pages/usage_config.html",
        nav="Usage config",
        title="Usage config",
        monitor_host=monitor_host,
    )


"""
HYPERVISORS
"""


@app.route("/isard-admin/admin/hypervisors", methods=["GET"])
@login_required
@isAdmin
def admin_hypervisors():
    return render_template(
        "admin/pages/hypervisors.html",
        title="Hypervisors",
        header="Hypervisors",
        nav="Hypervisors",
        monitor_host=monitor_host,
    )


@app.route("/isard-admin/admin/storage_nodes", methods=["GET"])
@login_required
@isAdmin
def storage_nodes():
    """
    Storage Nodes
    """
    return render_template(
        "admin/pages/storage_nodes.html",
        title="Storage Nodes",
        nav="Storage Nodes",
        monitor_host=monitor_host,
    )


"""
UPDATES
"""


@app.route("/isard-admin/admin/updates", methods=["GET"])
@login_required
@isAdmin
def admin_updates():
    return render_template(
        "admin/pages/updates.html",
        title="Downloads",
        nav="Downloads",
        monitor_host=monitor_host,
    )


"""
CONFIG
"""


@app.route("/isard-admin/admin/config", methods=["GET"])
@login_required
@isAdminManager
def admin_config():
    return render_template(
        "admin/pages/config.html",
        nav="Config",
        title="Config",
        monitor_host=monitor_host,
    )
