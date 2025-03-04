from rethinkdb import RethinkDB

r = RethinkDB()
from api import app

from ..libv2.flask_rethink import RDB

db = RDB(app)
db.init_app(app)

stable_status = ["Started", "Stopped", "Failed"]


def Users():
    with app.app_context():
        users = list(r.table("users").pluck("active").run(db.conn))
        roles = r.table("users").group("role").count().run(db.conn)
    users_count = len(users)
    users_active = len([u for u in users if u["active"]])
    return {
        "total": users_count,
        "status": {
            "enabled": users_active,
            "disabled": users_count - users_active,
        },
        "roles": roles,
    }


def Desktops():
    with app.app_context():
        total = r.table("domains").get_all("desktop", index="kind").count().run(db.conn)
        group_by_status = (
            r.table("domains")
            .get_all("desktop", index="kind")
            .group("status")
            .count()
            .run(db.conn)
        )
    return {
        "total": total,
        "status": group_by_status,
    }


def Templates():
    with app.app_context():
        templates = list(
            r.table("domains")
            .get_all("template", index="kind")
            .pluck("enabled")
            .run(db.conn)
        )
    templates_enabled = len([t for t in templates if t["enabled"]])
    return {
        "total": len(templates),
        "enabled": templates_enabled,
        "disabled": len(templates) - templates_enabled,
    }


def DomainsStatus():
    with app.app_context():
        domains = r.table("domains").group(index="kind_status").count().run(db.conn)
    d = {}
    for k, v in domains.items():
        if k[0] not in d:
            d[k[0]] = {}
        d[k[0]][k[1]] = v
    return d


def OtherStatus():
    with app.app_context():
        desktops = (
            r.table("domains")
            .get_all("desktop", index="kind")
            .pluck("category", "status", "kind")
            .group("category", "status")
            .count()
            .run(db.conn)
        )
        templates = (
            r.table("domains")
            .get_all("template", index="kind")
            .pluck("category", "status", "kind")
            .group("category", "status")
            .count()
            .run(db.conn)
        )
    result = {}
    for key, value in desktops.items():
        if key[1] in stable_status:
            continue
        if key[0] not in result.keys():
            result[key[0]] = {"desktops_wrong_status": {key[1]: value}}
        else:
            result[key[0]] = {
                **result[key[0]],
                **{"desktops_wrong_status": {key[1]: value}},
            }
    for key, value in templates.items():
        if key[1] == "Stopped":
            continue
        if key[0] not in result.keys():
            result[key[0]] = {"templates_wrong_status": {key[1]: value}}
        else:
            result[key[0]] = {
                **result[key[0]],
                **{"templates_wrong_status": {key[1]: value}},
            }
    return result


def Kind(kind):
    query = {}
    if kind == "desktops":
        query = r.table("domains").get_all("desktop", index="kind").pluck("id", "user")

    elif kind == "templates":
        query = r.table("domains").get_all("template", index="kind").pluck("id")

    elif kind == "users":
        query = r.table(kind).pluck("id", "role", "category", "group")

    elif kind == "hypervisors":
        query = r.table(kind).pluck("id", "status", "only_forced")

    with app.app_context():
        return list(query.run(db.conn))


def GroupByCategories():
    with app.app_context():
        query = {}
        categories = r.table("categories").pluck("id")["id"].run(db.conn)
        user_role = ["admin", "manager", "advanced", "user"]
        for category in categories:
            query[category] = {
                "users": {
                    "total": "",
                    "status": {"enabled": "", "disabled": ""},
                    "roles": {
                        "admin": "",
                        "manager": "",
                        "advanced": "",
                        "user": "",
                    },
                },
                "desktops": {
                    "total": "",
                    "status": {
                        "Started": "",
                        "Stopped": "",
                        "Failed": "",
                        "Unknown": "",
                        "Other": "",
                    },
                },
                "templates": {
                    "total": "",
                    "status": {"enabled": "", "disabled": ""},
                },
            }
            query[category]["users"]["total"] = (
                r.table("users")
                .get_all(category, index="category")
                .count()
                .run(db.conn)
            )
            query[category]["users"]["status"]["enabled"] = (
                r.table("users")
                .get_all(category, index="category")
                .filter({"active": True})
                .count()
                .run(db.conn)
            )
            query[category]["users"]["status"]["disabled"] = (
                r.table("users")
                .get_all(category, index="category")
                .filter({"active": False})
                .count()
                .run(db.conn)
            )
            for role in user_role:
                query[category]["users"]["roles"][role] = (
                    r.table("users")
                    .get_all(category, index="category")
                    .filter({"role": role})
                    .count()
                    .run(db.conn)
                )

            query[category]["desktops"]["total"] = (
                r.table("domains")
                .get_all(["desktop", category], index="kind_category")
                .count()
                .run(db.conn)
            )
            for status in stable_status:
                query[category]["desktops"]["status"][status] = (
                    r.table("domains")
                    .get_all(
                        ["desktop", status, category], index="kind_status_category"
                    )
                    .count()
                    .run(db.conn)
                )
            query[category]["desktops"]["status"]["Other"] = (
                r.table("domains")
                .get_all(["desktop", category], index="kind_category")
                .filter(
                    lambda desktop: r.not_(
                        r.expr(stable_status).contains(desktop["status"])
                    )
                )
                .count()
                .run(db.conn)
            )

            query[category]["templates"]["total"] = (
                r.table("domains")
                .get_all(["template", category], index="kind_category")
                .count()
                .run(db.conn)
            )
            query[category]["templates"]["status"]["enabled"] = (
                r.table("domains")
                .get_all(
                    ["template", True, category], index="template_enabled_category"
                )
                .count()
                .run(db.conn)
            )
            query[category]["templates"]["status"]["disabled"] = (
                r.table("domains")
                .get_all(
                    ["template", False, category], index="template_enabled_category"
                )
                .count()
                .run(db.conn)
            )
    return query


def CategoriesKindState(kind, state=False):
    with app.app_context():
        query = {}
        categories = r.table("categories").pluck("id")["id"].run(db.conn)
        for category in categories:
            if kind == "desktop":
                if state:
                    query[category] = {"desktops": {"status": {state: ""}}}
                    query[category]["desktops"]["status"][state] = (
                        r.table("domains")
                        .get_all(
                            ["desktop", state, category], index="kind_status_category"
                        )
                        .count()
                        .run(db.conn)
                    )
                    if state == "Other":
                        query[category]["desktops"]["status"]["Other"] = (
                            r.table("domains")
                            .get_all(["desktop", category], index="kind_category")
                            .filter(
                                lambda desktop: r.not_(
                                    r.expr(stable_status).contains(desktop["status"])
                                )
                            )
                            .count()
                            .run(db.conn)
                        )
                    return query
                else:
                    query[category] = {
                        "desktops": {
                            "total": "",
                            "status": {
                                "Started": "",
                                "Stopped": "",
                                "Failed": "",
                                "Unknown": "",
                                "Other": "",
                            },
                        }
                    }
                    query[category]["desktops"]["total"] = (
                        r.table("domains")
                        .get_all(["desktop", category], index="kind_category")
                        .count()
                        .run(db.conn)
                    )

                    for ds in stable_status:
                        query[category]["desktops"]["status"][ds] = (
                            r.table("domains")
                            .get_all(
                                ["desktop", ds, category], index="kind_status_category"
                            )
                            .count()
                            .run(db.conn)
                        )
                    query[category]["desktops"]["status"]["Other"] = (
                        r.table("domains")
                        .get_all(["desktop", category], index="kind_category")
                        .filter(
                            lambda desktop: r.not_(
                                r.expr(stable_status).contains(desktop["status"])
                            )
                        )
                        .count()
                        .run(db.conn)
                    )
                    return query

            elif kind == "template":
                if state == "enabled":
                    query[category] = {"templates": {"status": {"enabled": ""}}}
                    query[category]["templates"]["status"]["enabled"] = (
                        r.table("domains")
                        .get_all(
                            ["template", True, category],
                            index="template_enabled_category",
                        )
                        .count()
                        .run(db.conn)
                    )
                    return query

                elif state == "disabled":
                    query[category] = {"templates": {"status": {"disabled": ""}}}
                    query[category]["templates"]["status"]["disabled"] = (
                        r.table("domains")
                        .get_all(
                            ["template", False, category],
                            index="template_enabled_category",
                        )
                        .count()
                        .run(db.conn)
                    )
                    return query

                else:
                    query[category] = {
                        "templates": {
                            "total": "",
                            "status": {"enabled": "", "disabled": ""},
                        }
                    }
                    query[category]["templates"]["total"] = (
                        r.table("domains")
                        .get_all(["template", category], index="kind_category")
                        .count()
                        .run(db.conn)
                    )
                    query[category]["templates"]["status"]["enabled"] = (
                        r.table("domains")
                        .get_all(
                            ["template", True, category],
                            index="template_enabled_category",
                        )
                        .count()
                        .run(db.conn)
                    )
                    query[category]["templates"]["status"]["disabled"] = (
                        r.table("domains")
                        .get_all(
                            ["template", False, category],
                            index="template_enabled_category",
                        )
                        .count()
                        .run(db.conn)
                    )
                    return query


def CategoriesLimitsHardware():
    with app.app_context():
        query = {}
        categories = r.table("categories").pluck("id", "limits").run(db.conn)

        for category in categories:
            query[category["id"]] = {
                "Started desktops": "",
                "vCPUs": {"Limit": "", "Running": ""},
                "Memory": {"Limit": "", "Running": ""},
            }
            query[category["id"]]["Started desktops"] = (
                r.table("domains")
                .get_all(
                    ["desktop", "Started", category["id"]], index="kind_status_category"
                )
                .count()
                .run(db.conn)
            )

            # If unlimited
            if category["limits"] == False:
                query[category["id"]]["vCPUs"]["Limit"] = 0
                query[category["id"]]["Memory"]["Limit"] = 0
            else:
                query[category["id"]]["vCPUs"]["Limit"] = category["limits"]["vcpus"]
                query[category["id"]]["Memory"]["Limit"] = category["limits"]["memory"]

            query[category["id"]]["vCPUs"]["Running"] = (
                r.table("domains")
                .get_all(
                    ["desktop", "Started", category["id"]], index="kind_status_category"
                )["create_dict"]["hardware"]["vcpus"]
                .sum()
                .run(db.conn)
            )
            query[category["id"]]["Memory"]["Running"] = (
                r.table("domains")
                .get_all(
                    ["desktop", "Started", category["id"]], index="kind_status_category"
                )["create_dict"]["hardware"]["memory"]
                .sum()
                .run(db.conn)
            )
    return query


def CategoriesDeploys():
    with app.app_context():
        return (
            r.table("deployments")
            .merge(
                lambda dom: {
                    "category": r.table("users")
                    .get(dom["user"])["category"]
                    .default("None"),
                }
            )
            .group(r.row["category"])
            .count()
            .run(db.conn)
        )
