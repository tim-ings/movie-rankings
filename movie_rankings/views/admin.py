import flask
import json
import data
import auth


app_admin = flask.Blueprint('app_admin', __name__)


@app_admin.route('/admin/')
def view_all_polls():
    return flask.render_template('admin.html', c={
        'user': auth.get_user_context(auth.current_user_id()),
    })


