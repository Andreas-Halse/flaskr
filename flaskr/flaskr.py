from datetime import datetime
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash, jsonify
import requests
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)  # create the application instance :)
app.config.from_object(__name__)  # load config from this file , flaskr.py

# Load default config and override config from an environment variable
# TODO use for db path http://flask.pocoo.org/docs/0.12/config/#instance-folders
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))

# FLASKR_SETTINGS points to a config file
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def show_entries():
    db = get_db()
    # Include created_at in the SELECT statement to show the timpstamp
    cur = db.execute('SELECT title, text, created_at FROM entries ORDER BY id DESC')
    entries = cur.fetchall()
    echo_response = session.pop('postman_echo_response', None)
    return render_template('show_entries.html', entries=entries, echo_response=echo_response)

# format_response function to convert the todos to a JSON response
def format_response(todos):
    # Convert the todos to a list of dictionaries for JSON response
    todos_list = [dict(id=row['id'], title=row['title'], text=row['text'], created_at=row['created_at']) for row in todos]
    return jsonify(todos_list)

# Make a search function that takes a query string and returns the results
def search_todos(query):
    db = get_db()
    query = f"%{query}%"  # Prepare the query for LIKE pattern matching
    todos = db.execute('SELECT * FROM entries WHERE title LIKE ?', (query,)).fetchall()
    return format_response(todos)

# Adding the route for searching
@app.route('/api/search')
def search():
    query_param = request.args.get('q', '')  # Default to empty string if not provided
    return search_todos(query_param)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    title = request.form['title']
    text = request.form['text']
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Insert the todo entry
    db.execute('INSERT INTO entries (title, text, created_at) VALUES (?, ?, ?)',
               [title, text, created_at])
    db.commit()
    flash('New entry was successfully posted')

    # Prepare the todo data
    todo_data = {
        'title': title,
        'text': text,
        'created_at': created_at
    }
    # Send the HTTP POST request with the todo data as JSON
    response = requests.post('https://postman-echo.com/post', json=todo_data, verify=False)
    
    if response.status_code == 200:
        # Assuming response is JSON and storing it in the session
        session['postman_echo_response'] = response.json()
    else:
        session['postman_echo_response'] = {'error': 'Failed to get a valid response from Postman Echo'}

    return redirect(url_for('show_entries'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))
