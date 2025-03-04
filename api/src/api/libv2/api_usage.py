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

from datetime import datetime, timedelta

import pytz
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from isardvdi_common.api_exceptions import Error
from rethinkdb import RethinkDB

from api import app

from .flask_rethink import RDB
from .usage.common import get_default_consumption, get_params
from .usage.consolidate import substract_dicts
from .usage.desktop import ConsolidateDesktopConsumption
from .usage.media import ConsolidateMediaConsumption
from .usage.storage import ConsolidateStorageConsumption
from .usage.user import ConsolidateUserConsumption

r = RethinkDB()
db = RDB(app)
db.init_app(app)


def get_usage_consumption_between_dates(
    start_date, end_date, items_ids, item_type, grouping=None
):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    if items_ids is None:
        with app.app_context():
            items = list(
                r.table("usage_consumption")
                .pluck("item_id", "item_name")
                .distinct()
                .run(db.conn)
            )
    else:
        items = list(
            r.table("usage_consumption")
            .get_all(r.args(items_ids), index="item_id")
            .pluck("item_id", "item_name")
            .distinct()
            .run(db.conn)
        )
    data = []
    reset_dates = get_reset_dates(start_date, end_date)
    for current_day in range(0, (end_date - start_date).days + 1):
        current_day = start_date + timedelta(days=current_day)
        for item in items:
            item_data = get_item_date_consumption(
                current_day,
                item["item_id"],
                item_type,
                item["item_name"],
                grouping_params=grouping,
            )
            abs = item_data["abs"]
            # Reset only applies to desktops and users
            # It doesn't make sense in sizes or items created (storage/media)
            if item_type in ["desktop", "user"] and len(reset_dates):
                for date in reset_dates:
                    if current_day >= date:
                        # TODO: cache this
                        abs_reset_data = get_item_date_consumption(
                            date,
                            item["item_id"],
                            item_type,
                            item["item_name"],
                            grouping_params=grouping,
                        )["abs"]
                        abs = substract_dicts(item_data["abs"], abs_reset_data)
                        break
            data.append(
                {
                    "name": item["item_name"],
                    "date": current_day,
                    "inc": item_data["inc"],
                    "abs": abs,
                    "item_id": item["item_id"],
                }
            )
    return data


cache_usage_reset_date = TTLCache(maxsize=10, ttl=60)


@cached(
    cache_usage_reset_date, key=lambda start_date, end_date: f"{start_date}-{end_date}"
)
def get_reset_dates(start_date=None, end_date=None):
    # TODO: Check that it is doing what is supposed to do
    # Must return first reset date before start_date and all dates
    # between start_date and end_date in descending order (newest first)
    # If none found, return empty list
    # return [
    #     (
    #         datetime(2023, 9, 1)
    #         .astimezone()
    #         .replace(minute=0, hour=0, second=0, microsecond=0, tzinfo=pytz.utc)
    #     )
    #     + timedelta(days=-1)
    # ]
    within = []

    if start_date and end_date:
        with app.app_context():
            within = list(
                r.table("usage_reset_dates")
                .filter((r.row["date"] <= end_date))
                .order_by(r.desc("date"))["date"]
                .run(db.conn)
            )

    else:
        with app.app_context():
            within = list(
                r.table("usage_reset_dates")
                .order_by(r.desc("date"))["date"]
                .run(db.conn)
            )
    if len(within):
        result = within
        result.reverse()
        return result
    else:
        return []


def add_reset_date(reset_dates):
    with app.app_context():
        r.table("usage_reset_dates").delete().run(db.conn)
        for date in set(reset_dates):
            date = date.replace(tzinfo=pytz.timezone("UTC"))
            r.table("usage_reset_dates").insert({"date": date}).run(db.conn)
    cache_usage_reset_date.clear()


# Define a custom key function
def GSEC_KEY(
    start_date,
    end_date,
    items_ids=None,
    item_type=None,
    item_consumer=None,
    grouping_params=None,
    category_id=None,
):
    args = (
        start_date,
        end_date,
        tuple(items_ids) if items_ids else None,
        item_type,
        item_consumer,
        tuple(grouping_params),
        category_id,
    )
    return hashkey(args)


@cached(TTLCache(maxsize=200, ttl=60), key=GSEC_KEY)
def get_start_end_consumption(
    start_date,
    end_date,
    items_ids=None,
    item_type=None,
    item_consumer=None,
    grouping_params=None,
    category_id=None,
):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    app.logger.debug("Start date: %s", start_date)
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    if items_ids is None:
        with app.app_context():
            items = r.table("usage_consumption").get_all(
                item_consumer, index="item_consumer"
            )
            if category_id:
                items = items.pluck(
                    "item_id", "item_name", "item_consumer_category_id"
                ).filter({"item_consumer_category_id": category_id})
            else:
                items = items.pluck("item_id", "item_name")
            items = list(items.distinct().run(db.conn))
    else:
        with app.app_context():
            items = list(
                r.table("usage_consumption")
                .get_all(r.args(items_ids), index="item_id")
                .pluck("item_id", "item_name")
                .distinct()
                .run(db.conn)
            )
    data = []

    reset_dates = get_reset_dates(start_date, end_date)  # First should be the newest
    reset_start_date = None
    reset_end_date = None
    if item_type in ["desktop", "user"] and len(reset_dates):
        for reset_date in reset_dates:
            if reset_date <= start_date:
                reset_start_date = reset_date
                break
        if reset_dates[0] < end_date:
            reset_end_date = reset_dates[0]

    items_ids = [d["item_id"] for d in items]
    duplicated_items_ids = list(
        set([d["item_id"] for d in items if items_ids.count(d["item_id"]) > 1])
    )
    for item in items:
        start_data = get_item_date_consumption(
            start_date,
            item["item_id"],
            item_type,
            item["item_name"],
            grouping_params=grouping_params,
        )
        if reset_start_date:
            reset_start_data = get_item_date_consumption(
                reset_start_date,
                item["item_id"],
                item_type,
                item["item_name"],
                grouping_params=grouping_params,
            )
            start_data["abs"] = substract_dicts(
                start_data["abs"], reset_start_data["abs"]
            )
        end_data = get_item_date_consumption(
            end_date,
            item["item_id"],
            item_type,
            item["item_name"],
            grouping_params=grouping_params,
        )
        if reset_end_date:
            reset_end_data = get_item_date_consumption(
                reset_end_date,
                item["item_id"],
                item_type,
                item["item_name"],
                grouping_params=grouping_params,
            )
            end_data["abs"] = substract_dicts(end_data["abs"], reset_end_data["abs"])
        item["item_description"] = ""
        if item_consumer == "category":
            with app.app_context():
                item["item_description"] = (
                    r.table("categories")
                    .get(item["item_id"])
                    .default({"description": ""})["description"]
                    .run(db.conn)
                )
        data.append(
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "item_description": item["item_description"],
                "item_consumer": item_consumer,
                "start": start_data,
                "end": end_data,
                "duplicated_item_id": item["item_id"] in duplicated_items_ids,
            }
        )
    return data


# Define a custom key function
def GIDC_KEY(date, item_id, item_type, item_name, grouping_params=None):
    # DISABLED: This is not working properly
    # Randomly getting item date consumptions erroneusly
    args = (date, item_id, item_type, item_name, tuple(grouping_params))
    return hashkey(args)


# @cached(TTLCache(maxsize=100, ttl=60), key=GIDC_KEY)
def get_item_date_consumption(
    date, item_id, item_type, item_name, grouping_params=None
):
    if type(date) is str:
        date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    if grouping_params:
        pluck = (
            {"abs": grouping_params, "inc": grouping_params},
            "date",
            "item_name",
            "item_id",
            "item_type",
            "item_consumer",
        )
    else:
        pluck = (
            "date",
            "inc",
            "abs",
            "item_name",
            "item_id",
            "item_type",
            "item_consumer",
        )

    if grouping_params:
        default_consumption = get_default_consumption(grouping_params)
    else:
        default_consumption = get_default_consumption()
    with app.app_context():
        data = (
            r.table("usage_consumption")
            .get_all(item_id, index="item_id")
            .pluck(pluck)
            .filter((r.row["date"] <= date) & (r.row["item_type"] == item_type))
            .order_by("date")
            .nth(-1)
            .default(
                {
                    "name": item_name,
                    "date": date,
                    "inc": default_consumption,
                    "abs": default_consumption,
                    "item_id": item_id,
                    "item_type": item_type,
                }
            )
            .run(db.conn)
        )
        data["inc"] = (
            r.table("usage_consumption")
            .get_all(item_id, index="item_id")
            .pluck(pluck)
            .filter((r.row["date"] == date) & (r.row["item_type"] == item_type))
            .nth(0)
            .default(
                {
                    "inc": default_consumption,
                }
            )["inc"]
            .run(db.conn)
        )
    return data


@cached(TTLCache(maxsize=100, ttl=60))
def get_usage_distinct_items(item_consumer, start_date, end_date, item_category=None):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    query = (
        r.table("usage_consumption")
        .get_all(item_consumer, index="item_consumer")
        .merge(
            lambda doc: {
                "category_name": r.branch(
                    doc["item_consumer_category_id"].ne(None)
                    and (
                        doc["item_consumer"] in ["desktop", "template", "user", "group"]
                    ),
                    r.table("categories")
                    .get(doc["item_consumer_category_id"])
                    .default({"name": None})["name"],
                    None,
                ),
                "username": r.branch(
                    doc["item_consumer"] in ["desktop", "template"]
                    and doc["item_id"] != "_total_",
                    r.table("domains")
                    .get(doc["item_id"])
                    .default({"username": None})["username"],
                    None,
                ),
            }
        )
    )
    if item_category:
        query = query.pluck(
            "item_id",
            "item_name",
            "item_consumer_category_id",
            "category_name",
            "username",
        ).filter({"item_consumer_category_id": item_category})
    else:
        query = query.pluck("item_id", "item_name", "category_name", "username")
    with app.app_context():
        data = list(query.distinct().run(db.conn))
    return data


@cached(TTLCache(maxsize=10, ttl=60))
def get_usage_consumers(item_type):
    with app.app_context():
        return list(
            r.table("usage_consumption")
            .get_all(item_type, index="item_type")
            .pluck("item_consumer")
            .distinct()["item_consumer"]
            .run(db.conn)
        )


def count_usage_consumers():
    with app.app_context():
        return r.table("usage_consumption").count().run(db.conn)


def consolidate_consumptions(item_type=None, total_days=2):
    if total_days == "all":
        with app.app_context():
            beggining_time = (
                r.table("logs_" + item_type)
                .order_by(index="started_time")
                .nth(0)["started_time"]
                .run(db.conn)
            )
            total_days = int(
                (datetime.now(pytz.utc) - beggining_time).total_seconds() / 60 / 60 / 24
            )
        pass
    else:
        total_days = int(total_days)

    if not item_type:
        # Storage can only be consolidated for previous day
        ConsolidateStorageConsumption()
        # Media can only be consolidated for previous day
        ConsolidateMediaConsumption()

        # Desktop and Users accepts multiple days. To consolidate last week:
        # ConsolidateDesktopConsumption(3)
        if total_days == "all":
            pass
        else:
            for i in list(reversed(range(1, total_days))):
                ConsolidateDesktopConsumption(days_before=i)
                ConsolidateUserConsumption(days_before=i)

    elif item_type == "desktops":
        for i in list(reversed(range(1, total_days))):
            ConsolidateDesktopConsumption(days_before=i)

    elif item_type == "users":
        for i in list(reversed(range(1, int(total_days)))):
            ConsolidateUserConsumption(days_before=i)

    elif item_type == "storage":
        ConsolidateStorageConsumption()

    elif item_type == "media":
        ConsolidateMediaConsumption()

    else:
        raise Error(
            "bad_request",
            "Item type " + item_type + " not valid for consumption calculation",
        )


## VIEWS: Usage grouping

cache_usage_grouping = TTLCache(maxsize=10, ttl=60)


@cached(cache_usage_grouping)
def get_usage_groupings():
    params = get_params()
    groupings = []
    for item_type in params.keys():
        system_parameters = [sp["id"] for sp in params[item_type] if not sp["custom"]]
        custom_parameters = [cp["id"] for cp in params[item_type] if cp["custom"]]

        groupings = groupings + [
            {
                "id": "_all",
                "item_type": item_type,
                "item_sub_type": "all",
                "name": f"All {item_type} parameters",
                "desc": f"All {item_type} system and custom parameters",
                "parameters": system_parameters + custom_parameters,
            },
            {
                "id": "_system",
                "name": f"All {item_type} system parameters",
                "item_type": item_type,
                "item_sub_type": "system",
                "desc": f"All {item_type} system parameters",
                "parameters": system_parameters,
            },
            {
                "id": "_custom",
                "name": f"All {item_type} custom parameters",
                "item_type": item_type,
                "item_sub_type": "custom",
                "desc": f"All {item_type} custom parameters",
                "parameters": custom_parameters,
            },
        ]
    with app.app_context():
        groupings = groupings + list(r.table("usage_grouping").run(db.conn))
    return groupings


cache_usage_grouping_dropdown = TTLCache(maxsize=10, ttl=60)


@cached(cache_usage_grouping_dropdown)
def get_usage_groupings_dropdown():
    params = get_params()
    groupings = {"system": {}, "custom": {}}
    for item_type in params:
        system_parameters = [sp["id"] for sp in params[item_type] if not sp["custom"]]
        custom_parameters = [cp["id"] for cp in params[item_type] if cp["custom"]]

        groupings["system"][item_type] = [
            {
                "id": "_all",
                "name": f"All {item_type} parameters",
                "item_type": item_type,
                "desc": f"All {item_type} system and custom parameters",
                "parameters": system_parameters + custom_parameters,
            },
            {
                "id": "_system",
                "name": f"All {item_type} system parameters",
                "item_type": item_type,
                "desc": f"All {item_type} system parameters",
                "parameters": system_parameters,
            },
            {
                "id": "_custom",
                "name": f"All {item_type} custom parameters",
                "item_type": item_type,
                "desc": f"All {item_type} custom parameters",
                "parameters": custom_parameters,
            },
        ]
        with app.app_context():
            groupings["custom"][item_type] = list(
                r.table("usage_grouping").filter({"item_type": item_type}).run(db.conn)
            )

    return groupings


def add_usage_grouping(data):
    with app.app_context():
        r.table("usage_grouping").insert(data).run(db.conn)
        cache_usage_grouping.clear()
        cache_usage_grouping_dropdown.clear()
    return True


def update_usage_grouping(data):
    with app.app_context():
        r.table("usage_grouping").get(data["id"]).update(data).run(db.conn)
        cache_usage_grouping.clear()
        cache_usage_grouping_dropdown.clear()
    return True


def delete_usage_grouping(grouping_id):
    try:
        with app.app_context():
            r.table("usage_grouping").get(grouping_id).delete().run(db.conn)
            cache_usage_grouping.clear()
            cache_usage_grouping_dropdown.clear()
    except:
        raise Error(
            "not_found",
            "Parameter grouping with ID " + grouping_id + " not found in database",
        )
    return True


## VIEWS: Usage limits

cache_usage_limits = TTLCache(maxsize=10, ttl=60)


@cached(cache_usage_limits)
def get_usage_limits():
    with app.app_context():
        return list(r.table("usage_limit").run(db.conn))


def add_usage_limits(name, desc, limits):
    check_usage_limits(limits)
    with app.app_context():
        r.table("usage_limit").insert(
            {
                "name": name,
                "desc": desc,
                "limits": limits,
            }
        ).run(db.conn)
        cache_usage_limits.clear()
    return True


def update_usage_limits(id, name, desc, limits):
    check_usage_limits(limits)
    with app.app_context():
        r.table("usage_limit").get(id).update(
            {
                "name": name,
                "desc": desc,
                "limits": limits,
            }
        ).run(db.conn)
        cache_usage_limits.clear()
    return True


def delete_usage_limits(limit_id):
    try:
        with app.app_context():
            r.table("usage_limit").get(limit_id).delete().run(db.conn)
            cache_usage_limits.clear()
    except:
        raise Error("not_found", "Limit with ID" + limit_id + " not found in database")
    return True


def check_usage_limits(limits):
    if not all(
        [
            limits["hard"] >= limits["exp_min"],
            limits["hard"] >= limits["exp_max"],
            limits["hard"] >= limits["soft"],
        ]
    ):
        raise Error(
            "bad_request",
            "The hard limit must be higher than or equal to all other limit values.",
        )

    if not (limits["exp_max"] > limits["exp_min"]):
        raise Error(
            "bad_request", "Expected maximum must be greater than the expected minimum"
        )

    if not (limits["soft"] > limits["exp_min"]):
        raise Error(
            "bad_request", "Expected minimum can not be greater than the soft limit"
        )


## VIEWS: Usage parameters

cache_usage_parameters = TTLCache(maxsize=10, ttl=60)


def get_usage_parameters(ids=None):
    with app.app_context():
        if ids:
            return list(r.table("usage_parameter").get_all(r.args(ids)).run(db.conn))
        else:
            return list(r.table("usage_parameter").run(db.conn))


def add_usage_parameters(data):
    with app.app_context():
        r.table("usage_parameter").insert(
            {
                "custom": data["custom"],
                "default": 0,
                "desc": data["desc"],
                "formula": data["formula"],
                "id": data["id"],
                "item_type": data["item_type"],
                "name": data["name"],
                "units": data["units"],
            }
        ).run(db.conn)
        cache_usage_parameters.clear()
    return True


def update_usage_parameters(data):
    if data["custom"]:
        with app.app_context():
            r.table("usage_parameter").get(data["id"]).update(data).run(db.conn)
            cache_usage_parameters.clear()
    else:
        raise Error("forbidden", "Only custom parameters can be edited")
    return True


def delete_usage_parameters(parameter_id):
    try:
        with app.app_context():
            r.table("usage_parameter").get(parameter_id).delete().run(db.conn)
            cache_usage_parameters.clear()
    except:
        raise Error(
            "not_found",
            "Parameter with ID " + parameter_id + " not found in database",
        )
    return True


## VIEWS: Usage credits


def get_usage_credits(item_id, item_type, grouping_id, start_date, end_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    with app.app_context():
        credit = list(
            r.table("usage_credit")
            .get_all(
                [item_id, item_type, grouping_id], index="item_id-item_type-grouping"
            )
            .run(db.conn)
        )
    if not len(credit):
        return [
            {
                "limits": None,
                "start_date": start_date.strftime("%Y-%m-%d %H:%M%z"),
                "end_date": end_date.strftime("%Y-%m-%d %H:%M%z"),
            }
        ]
    # First check if there is a bigger credit interval than interval requested
    outer = [
        c
        for c in credit
        if c["start_date"] <= start_date
        and (not c["end_date"] or c["end_date"] >= end_date)
    ]
    if len(outer):
        if len(outer) > 1:
            raise Error("internal_server", "More than one outer credit interval found")
        outer[0]["start_date"] = start_date.strftime("%Y-%m-%d %H:%M%z")
        outer[0]["end_date"] = end_date.strftime("%Y-%m-%d %H:%M%z")
        # We will return always a list, even if it is only one item.
        return outer

    # It must only be one credit interval maximum matching before and after
    before = [
        c
        for c in credit
        if c["start_date"] <= start_date
        and (
            c["end_date"]
            and (c["end_date"] >= start_date and c["end_date"] <= end_date)
        )
    ]
    if len(before) > 1:
        raise Error("internal_server", "More than one before credit interval found")
    inner = [
        c
        for c in credit
        if c["start_date"] >= start_date
        and (c["end_date"] and c["end_date"] <= end_date)
    ]
    after = [
        c
        for c in credit
        if c["start_date"] <= end_date
        and (not c["end_date"] or c["end_date"] >= end_date)
    ]
    if len(after) > 1:
        raise Error("internal_server", "More than one after credit interval found")

    if not len(before + inner + after):
        # No limits found
        return [
            {
                "limits": None,
                "start_date": start_date.strftime("%Y-%m-%d %H:%M%z"),
                "end_date": end_date.strftime("%Y-%m-%d %H:%M%z"),
            }
        ]
    if len(before):
        before[0]["start_date"] = start_date
    else:
        before = [
            {
                "limits": None,
                "start_date": start_date,
                "end_date": inner[0]["start_date"]
                if len(inner)
                else after[0]["start_date"]
                if len(after)
                else end_date,
            }
        ]
    if len(after):
        after[0]["end_date"] = end_date
    else:
        after = [
            {
                "limits": None,
                "start_date": inner[-1]["end_date"]
                if len(inner)
                else before[0]["end_date"]
                if len(before)
                else start_date,
                "end_date": end_date,
            }
        ]
    all_intervals = before + inner + after
    for interval in all_intervals:
        interval["start_date"] = (
            interval["start_date"].strftime("%Y-%m-%d %H:%M%z")
            if not isinstance(interval["start_date"], str)
            else interval["start_date"]
        )
        interval["end_date"] = (
            interval["end_date"].strftime("%Y-%m-%d %H:%M%z")
            if not isinstance(interval["end_date"], str)
            else interval["end_date"]
        )
    return all_intervals


@cached(TTLCache(maxsize=10, ttl=60))
def get_usage_credits_by_id(credits_id):
    try:
        with app.app_context():
            return r.table("usage_credit").get(credits_id).run(db.conn)
    except:
        raise Error("not_found", "Category credit ID not found in database")


cache_usage_credits = TTLCache(maxsize=10, ttl=60)


@cached(cache_usage_credits)
def get_all_usage_credits():
    with app.app_context():
        return list(
            r.table("usage_credit")
            .merge(
                lambda row: {
                    "category_name": r.table("categories")
                    .get(row["item_id"])
                    .default({"name": ""})["name"],
                    "item_description": r.table("categories")
                    .get(row["item_id"])
                    .default({"description": ""})["description"],
                }
            )
            .merge(
                lambda row: {
                    "grouping_name": r.table("usage_grouping")
                    .get(row["grouping_id"])
                    .default({"name": row["grouping_id"]})["name"]
                }
            )
            .run(db.conn)
        )


def add_usage_credit(data):
    # TODO: Check if it overlaps with another interval
    # (same category and its start_date is earlier than
    # the end_date we want to set)

    # Cut/Delete existing overlapping intervals
    cut_existing_usage_credits(
        data["item_id"],
        data["item_type"],
        data["grouping_id"],
        data["start_date"],
        data["end_date"],
    )

    with app.app_context():
        limits = (
            r.table("usage_limit")
            .get(data["limit_id"])
            .pluck("id", "name", "desc", "limits")
            .run(db.conn)
        )
        r.table("usage_credit").insert(
            {
                "item_id": data["item_id"],
                "item_consumer": data["item_consumer"],
                "item_type": data["item_type"],
                "grouping_id": data["grouping_id"],
                "start_date": data["start_date"],
                "end_date": data["end_date"],
                "limits": limits.get("limits"),
                "limits_id": limits.get("id"),
                "limits_desc": limits.get("desc"),
                "limits_name": limits.get("name"),
            }
        ).run(db.conn)
        cache_usage_credits.clear()
    return True


def update_usage_credit(data):
    if (
        data.get("item_id")
        or data.get("item_type")
        or data.get("grouping_id")
        or data.get("start_date")
        or data.get("end_data")
    ):
        credit = get_usage_credits_by_id(data["id"])
        data["grouping_id"] = credit["grouping_id"]
        data["item_type"] = credit["item_type"]
        data["item_id"] = credit["item_id"]

        cut_existing_usage_credits(
            data["item_id"],
            data["item_type"],
            data["grouping_id"],
            data["start_date"],
            data["end_date"],
        )
    if data.get("limits"):
        check_usage_limits(data.get("limits"))
    with app.app_context():
        r.table("usage_credit").get(data["id"]).update(data).run(db.conn)
        cache_usage_credits.clear()
    return True


def delete_usage_credit(credit_id):
    try:
        with app.app_context():
            r.table("usage_credit").get(credit_id).delete().run(db.conn)
            cache_usage_credits.clear()
    except:
        raise Error(
            "not_found", "Credit with ID " + credit_id + " not found in database"
        )
    return True


def cut_existing_usage_credits(item_id, item_type, grouping_id, start_date, end_date):
    if not end_date:
        end_date = datetime.now(pytz.utc)

    with app.app_context():
        credit = list(
            r.table("usage_credit")
            .get_all(
                [item_id, item_type, grouping_id], index="item_id-item_type-grouping"
            )
            .run(db.conn)
        )

    if not len(credit):
        return

    # First check if there is a bigger credit interval than interval requested
    outer = [
        c
        for c in credit
        if c["start_date"] <= start_date
        and (not c["end_date"] or c["end_date"] >= end_date)
    ]
    if len(outer):
        if len(outer) > 1:
            raise Error("internal_server", "More than one outer credit interval found")
        app.logger.warning(
            f"Existing credit interval {outer[0]['id']} end_date {outer[0]['end_date'].date() if outer[0]['end_date'] else None} cutted to {(start_date+timedelta(days=-1)).date()}"
        )
        outer[0]["end_date"] = start_date + timedelta(days=-1)
        with app.app_context():
            r.table("usage_credit").get(outer[0]["id"]).update(outer[0]).run(db.conn)
            cache_usage_credits.clear()
        return

    # It must only be one credit interval maximum matching before and after
    before = [
        c
        for c in credit
        if c["start_date"] <= start_date
        and (
            c["end_date"]
            and (c["end_date"] >= start_date and c["end_date"] <= end_date)
        )
    ]
    if len(before):
        if len(before) > 1:
            raise Error("internal_server", "More than one before credit interval found")
        app.logger.warning(
            f"Existing credit interval {before[0]['id']} end_date {before[0]['end_date'].date() if before[0]['end_date'] else None} cutted to {(start_date+timedelta(days=-1)).date()}"
        )
        before[0]["end_date"] = start_date + timedelta(days=-1)
        with app.app_context():
            r.table("usage_credit").get(before[0]["id"]).update(before[0]).run(db.conn)
            cache_usage_credits.clear()
        return

    inner = [
        c
        for c in credit
        if c["start_date"] >= start_date
        and (c["end_date"] and c["end_date"] <= end_date)
    ]
    if len(inner):
        if len(inner) > 1:
            raise Error("internal_server", "More than one inner credit interval found")
        app.logger.warning(
            f"Existing credit interval {inner[0]['id']} {inner[0]['start_date'].date()}/{inner[0]['end_date'].date() if inner[0]['end_date'] else None} removed as is inside {start_date.date()}/{end_date.date()}"
        )
        with app.app_context():
            r.table("usage_credit").get(inner[0]["id"]).delete().run(db.conn)
            cache_usage_credits.clear()
        return

    after = [
        c
        for c in credit
        if c["start_date"] <= end_date
        and (not c["end_date"] or c["end_date"] >= end_date)
    ]
    if len(after):
        if len(after) > 1:
            raise Error("internal_server", "More than one after credit interval found")
        app.logger.warning(
            f"Existing credit interval start_date {after[0]['start_date'].date()} cutted to {(end_date+timedelta(days=1)).date()}"
        )
        after[0]["start_date"] = end_date + timedelta(days=1)
        with app.app_context():
            r.table("usage_credit").get(after[0]["id"]).update(after[0]).run(db.conn)
            cache_usage_credits.clear()
    return


def unify_item_name(item_id):
    with app.app_context():
        current_name = (
            r.table("usage_consumption")
            .get_all(item_id, index="item_id")
            .order_by("date")
            .run(db.conn)
        )[-1]["item_name"]
        r.table("usage_consumption").get_all(item_id, index="item_id").filter(
            lambda uc: uc["item_name"] != current_name
        ).update({"item_name": current_name}).run(db.conn)
    get_start_end_consumption.cache_clear()
    return current_name
