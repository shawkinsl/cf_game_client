import os
from datetime import timedelta
from functools import update_wrapper
from flask import Flask, jsonify, request, make_response
from flask.templating import render_template
from market import get_long_short_term_averages, realstring_dict
from pw_client import LeanPWDB
from pw_client import PWClient

__author__ = 'shawkins'

app = Flask(__name__)


# needed since api.gitsubmit is a different domain than gitsubmit
def crossdomain(app=None, origin=None, methods=None, headers='Origin, X-Requested-With, Content-Type, Authorization, Accept',
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Expose-Headers'] = 'is_tree'
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
@app.route('/')
@crossdomain(app=app, origin='*', methods=["GET"])
def hw():
    return "welcome to the dashboard api, nerd. this doesn't do anything. what are you doing here? get out."


@app.route('/graph_data/market/days=<int:days>/')
@crossdomain(app=app, origin='*', methods=["GET"])
def market_data(days):
    pwdb = LeanPWDB()
    total_minutes = days * 24 * 60
    num_records = total_minutes / 5
    long_term_averages, short_term_averages = get_long_short_term_averages(pwdb)
    long_term_averages = long_term_averages[-num_records:]
    short_term_averages = short_term_averages[-num_records:]
    last_record = long_term_averages[-1]
    types = realstring_dict.keys()
    return jsonify({"long_term_averages": long_term_averages, "short_term_averages": short_term_averages,
                    "last": last_record, "types": types})

@app.route('/defendability/')
@crossdomain(app=app, origin='*', methods=["GET"])
def defendability():
    pwdb = LeanPWDB()
    latest_list = pwdb.get_latest_nation_cache_list()
    nations_out = []
    avg_def_factor = 0
    for nation in latest_list["nations"]:
        def_factor = nation["defendability_factor"]
        avg_def_factor += def_factor

        action_priority = nation["action_priority"]

        obj_out = {'name': nation["name"],
                   'id': nation["nation_id"],
                   'score': nation["score"],
                   'num_cities': len(nation['cities']),
                   'percent_military_score': nation["percent_score_military"],
                   'def_factor': def_factor,
                   'action_priority': action_priority}

        nations_out.append(obj_out)
    avg_def_factor /= float(len(latest_list["nations"]))
    return jsonify({"list": nations_out, "avg_def_factor": avg_def_factor})


@app.route('/dashboard_beta/')
def dashboard_beta():
    return render_template('pages/index.html')

app.debug = True
if __name__ == "__main__":
    app.run("0.0.0.0", 8091)
