import flask
import app.data as data
import json
import os
import requests
from flask_dance.contrib.facebook import make_facebook_blueprint, facebook

app = flask.Flask(__name__, static_url_path='/static')
app.secret_key = 'debug_key'
blueprint = make_facebook_blueprint(
    client_id=os.environ.get('FACEBOOK_CLIENTID'),
    client_secret=os.environ.get('FACEBOOK_SECRET'),
)
app.register_blueprint(blueprint, url_prefix='/login')
data.init_db()


def is_authenticated():
    return 'user_id' in flask.session


def get_authed_user_id():
    return flask.session['user_id']


def try_login_user():
    if facebook.token and 'user_id' not in flask.session:
        # ask FB for account ID
        res = requests.get('https://graph.facebook.com/me?access_token=' + facebook.token['access_token'])
        fb_json = res.json()
        # try and get the use from out local DB
        user = data.get_user(fb_json['id'])
        # if we havent seen this user before, register them
        if not user:
            data.register_user(fb_json['id'], fb_json['name'])
        # save the users ID to our session
        flask.session['user_id'] = fb_json['id']


def get_user_context():
    user_name = data.get_user(flask.session['user_id'])[1]
    res = requests.get(
        'https://graph.facebook.com/v3.2/' + flask.session['user_id'] + '/picture?redirect=false&access_token=' +
        facebook.token['access_token'])
    avatar_url = "https://i.imgur.com/IGUApaz.jpg"
    if res.ok:
        avatar_url = res.json()['data']['url']
    return {
        'name': user_name,
        'avatar_url': avatar_url,
        'id': flask.session['user_id']
    }


@app.route('/')
def view_index():
    try_login_user()
    if not is_authenticated():
        return flask.redirect(flask.url_for('facebook.login'))
    else:
        movies = data.get_all_movies()
        movies = data.prepare_movie_list(movies, get_authed_user_id())
        movies.sort(key=lambda x: -x['popularity'])
        return flask.render_template('index.html', context={
            'user': get_user_context(),
            'movies': movies[:50]
        })


@app.route('/search', methods=['POST', 'GET'])
def view_search():
    if flask.request.method == 'POST':
        result = flask.request.form
        term_str = result['terms']
        terms = term_str.split(' ')
        movies = data.search_movies(terms)
        movies = data.prepare_movie_list(movies, get_authed_user_id())
        return flask.render_template('index.html', context={
            'user': get_user_context(),
            'movies': movies[:50]
        })


@app.route('/user/<user_id>')
def view_user(user_id):
    movies = data.get_user_fav_movies(user_id)
    movies = data.prepare_movie_list(movies, get_authed_user_id())
    return flask.render_template('profile.html', context={
        'user': get_user_context(),
        'movies': movies[:50]
    })


@app.route('/api/1/vote/<movie_id>')
def api_toggle_vote(movie_id):
    if not is_authenticated():
        return json.dumps({
            'success': False,
            'message': 'You are not logged in'
        })
    vote_status = data.toggle_vote(flask.session['user_id'], movie_id)
    return json.dumps({
        'vote': vote_status,
    })


def main():
    app.run(host='127.0.0.1', port='443', debug=True, ssl_context='adhoc')


if __name__ == '__main__':
    main()
