# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

from functools import wraps
from flask import Flask, abort, redirect, url_for, request, render_template
from flask_login import current_user, logout_user

from .LoginViews import logout
from webapp import app
import json

# from ..lib.log import * 

import rethinkdb as r
from ..lib.flask_rethink import RethinkDB
db = RethinkDB(app)
db.init_app(app)

def ownsid(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_user.role == 'admin': return fn(*args, **kwargs)
        try:
            myargs = request.get_json(force=True)
        except:
            myargs = request.form.to_dict()
        try:
            id = kwargs['id']
        except:
            try:
                id = myargs['pk']
            except:
                id = myargs['id']
        if id.startswith('_'+current_user.id) or (current_user.role == 'manager' and current_user.category == id.split('-')[1]):
            return fn(*args, **kwargs)

        logout_user()
        return render_template('login_category.html', category=False)
    return decorated_view

def ownsidortag(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_user.role == 'admin': return fn(*args, **kwargs)
        try:
            myargs = request.get_json(force=True)
        except:
            myargs = request.form.to_dict()
        try:
            id = kwargs['id']
        except:
            try:
                id = myargs['pk']
            except:
                id = myargs['id']
        if current_user.role == 'manager' and current_user.category == id.split('-')[1]: return fn(*args, **kwargs)
        with app.app_context():
            domain = r.table('domains').get(id).pluck('id','tag').run(db.conn)
        if domain != None:
            if domain.get('id','').startswith('_'+current_user.id): return fn(*args, **kwargs)
            if current_user.role == 'advanced' and domain.get('tag','').startswith('_'+current_user.id): return fn(*args, **kwargs)
        logout_user()
        return render_template('login_category.html', category=False)
    return decorated_view

def checkRole(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_user.role == 'user': return render_template('pages/desktops.html', title="Desktops", nav="Desktops")
        return fn(*args, **kwargs)
    return decorated_view

def isAdvanced(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_user.role == "advanced":
            return fn(*args, **kwargs)
        logout_user()
        return render_template('login_category.html', category=False)
    return decorated_view