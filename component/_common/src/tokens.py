#
#   Copyright © 2023 Josep Maria Viñolas Auquer
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

import logging as log
import os

import gevent
from flask import request
from jose import jwt
from rethinkdb import r

from .api_exceptions import Error
from .api_logs_users import LogsUsers


def get_header_jwt_payload():
    return get_token_payload(get_token_auth_header())


def get_auto_register_jwt_payload():
    register_payload = get_token_payload(get_token_auth_header())
    login_payload = get_token_payload(get_token_header("Login-Claims"))

    register_payload["role"] = login_payload["role_id"]
    register_payload["group"] = login_payload["group_id"]

    return register_payload


def get_token_header(header):
    """Obtains the Access Token from the a Header"""
    auth = request.headers.get(header, None)
    if not auth:
        raise Error(
            "unauthorized",
            "Authorization header is expected",
        )

    parts = auth.split()
    if parts[0].lower() != "bearer":
        raise Error(
            "unauthorized",
            "Authorization header must start with Bearer",
        )
    elif len(parts) == 1:
        raise Error("bad_request", "Token not found")
    elif len(parts) > 2:
        raise Error(
            "unauthorized",
            "Authorization header must be Bearer token",
        )

    return parts[1]  # Token


def get_token_auth_header():
    return get_token_header("Authorization")


def get_expired_user_data(token):
    try:
        claims = jwt.get_unverified_claims(token)
    except:
        return None
    try:
        if claims.get("kid") == "isardvdi":
            return claims.get("data")
        elif claims.get("kid") == "isardvdi-viewer" and claims.get("data").get(
            "desktop_id"
        ):
            return claims.get("data")
        else:
            # Not a system secret
            return None
    except Exception as e:
        log.debug(e)
    return None


def get_token_payload(token):
    try:
        claims = jwt.get_unverified_claims(token)
    except:
        raise Error(
            "unauthorized",
            "Bad token format",
        )
    try:
        if claims.get("kid") == "isardvdi":
            secret = os.environ.get("API_ISARDVDI_SECRET")
        elif claims.get("kid") == "isardvdi-viewer":
            secret = os.environ.get("API_ISARDVDI_SECRET")
            if not claims.get("data").get("desktop_id"):
                raise Error(
                    "unauthorized",
                    "Not authorized viewer token",
                )
        elif claims.get("kid") == "isardvdi-hypervisors":
            secret = os.environ.get("API_HYPERVISORS_SECRET")
        else:
            # Not a system secret
            raise Error(
                "unauthorized",
                "Bad token Key ID",
            )
    except:
        raise Error(
            "unauthorized",
            "Unable to parse authentication token",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options=dict(verify_aud=False, verify_sub=False, verify_exp=True),
        )
    except jwt.ExpiredSignatureError:
        raise Error(
            "unauthorized",
            "Token expired",
            description_code="token_expired",
            data=get_expired_user_data(token),
        )
    except jwt.JWTClaimsError:
        raise Error(
            "unauthorized",
            "Incorrect claims, please check the audience and issuer",
        )
    except Exception:
        raise Error(
            "unauthorized",
            "Unable to parse authentication token",
        )
    if payload.get("data", False):
        try:
            gevent.spawn(LogsUsers, payload)
        except Exception as e:
            log.warning("Unable to update user logs")
        return payload["data"]
    return payload
