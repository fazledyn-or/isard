# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

from functools import wraps
from api import app
import json, os
from flask import request
from rethinkdb import RethinkDB; r = RethinkDB()
from rethinkdb.errors import ReqlTimeoutError

from flask import Flask, request, jsonify, _request_ctx_stack
# from flask_cors import cross_origin
from jose import jwt

from ..libv2.log import log
import traceback

from ..libv2.flask_rethink import RDB
db = RDB(app)
db.init_app(app)

# secret=os.environ['API_ISARDVDI_SECRET']

def get_header_jwt_payload():
    return get_token_payload(get_token_auth_header())
    
def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description":
                        "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description":
                        "Authorization header must start with"
                        " Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description":
                        "Authorization header must be"
                        " Bearer token"}, 401)

    token = parts[1]
    return token


def get_token_payload(token):
    try:
        claims=jwt.get_unverified_claims(token)
        secret_data=app.ram['secrets'][claims['kid']]
        # Check if the token has the correct category
        if secret_data['role_id'] == 'manager' and secret_data['category_id'] != claims['data']['category_id']:
            raise AuthError({"code": "unauthorized",
                "description":
                "Not authorized category"
                " token."}, 500)
    except Exception as e:
        print(e)
        raise AuthError({"code": "invalid_parameters",
                        "description":
                        "Unable to parse authentication parameters"
                        " token."}, 401)
    try:
        payload = jwt.decode(
            token,
            secret_data['secret'], 
            algorithms=["HS256"],
            options=dict(
                        verify_aud=False,
                        verify_sub=False,
                        verify_exp=True,
                        )
        )
    except jwt.ExpiredSignatureError:
        log.info('Token expired')
        raise AuthError({"code": "token_expired",
                        "description": "token is expired"}, 401)
    except jwt.JWTClaimsError:
        raise AuthError({"code": "invalid_claims",
                        "description":
                        "incorrect claims,"
                        "please check the audience and issuer"}, 401)
    except Exception:
        log.debug(traceback.format_exc())
        raise AuthError({"code": "invalid_header",
                        "description":
                        "Unable to parse authentication"
                        " token."}, 401)
    if payload.get('data',False): return payload['data']
    return payload

# Error handler
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response