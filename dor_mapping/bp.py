import functools
import psycopg
from flask import (
    Blueprint, g, redirect, render_template, request, session, url_for, abort, current_app)
from . import postgres_code as postgres
from . import db

bp = Blueprint('auth', __name__)

def print_all(route): 
    print(f'{route = }')
    for i in g: 
        print(f'g.{i} = {g.get(i)}')
    print(f'{session = }')

@bp.before_app_request
def load_logged_in_user():
    '''
    Register this function that runs before the view function, no matter what 
    URL is requested.
    '''
    g.user = session.get('user') 
    g.named_version = session.get('named_version')
    if current_app.config['TESTING'] == True: 
        g.testing = True

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.logout'))

        return view(**kwargs)

    return wrapped_view

@bp.route('/', methods=['POST', 'GET'])
def login():
    '''
    Present a log in page for the user, and if username/password are valid: 
    1. Log them in 
    2. Confirms that they can form a db connection
    3. Save their Begin edit session in their name
    If username/password are not valid, return a warning message on the same page.
    '''
    session.clear()
    error = None
    if request.method == 'POST':
        user, password = request.form['username'], request.form['password']
        print(f'{user = }')
        error = None
        try: 
            session['user'] = user
            session['named_version'] = user.replace('.', '_')
            db.get_db(user, password) # Verify user can log in
            db_conn = db.get_default_db(session['named_version'])
            postgres.sde.end_edit_version(db_conn, session['named_version'])
            postgres.commit_transactions(db_conn, current_app.config.get('COMMIT', True))
            print_all(f'login_{request.method}')
            return redirect(url_for('auth.record'))                
        except (psycopg.OperationalError, ValueError) as e: 
            print(f'error: {e}')
            error = 'Invalid username/password'
        print_all(f'login_{request.method}')
    return render_template('auth/login.html', error=error, testing=current_app.config['TESTING'])
    
@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    '''
    Logout the user, removing the request information and ending edit session
    '''
    db.close_db()
    g.pop('user', None)
    g.pop('named_version', None)
    session.clear()
    print_all(f'logout_{request.method}')
    return redirect(url_for('auth.login'))

@bp.route('/record', methods=['POST', 'GET'])
@login_required
def record(): 
    '''
    Present record submission form, and: 
    1. If record is found, initiate all database tasks and return table of updated 
    records to user, committing transactions
    2. If no records are found, return error message to user and remain on page
    '''
    error = None
    db_conn = db.get_default_db(session['named_version'])
    if request.method == 'POST':
        try: 
            print(f'Initiating database transactions')
            headers, results = db.initiate(db_conn, request.form)
            print(f'{request.form = }')
        except Exception as e: 
            postgres.commit_transactions(db_conn, False)
            print(e)
            abort(500, str(e))
        postgres.sde.end_edit_version(db_conn, session['named_version'])
        postgres.commit_transactions(db_conn, current_app.config.get('COMMIT', True))
        if len(results) == 0: 
            error = 'No valid matching records found - check spelling and try again'
            print(error)
        if error == None: 
            print_all(f'record_{request.method}')
            return render_template('auth/result.html', 
                headers=headers, results=results, n=len(results), testing=current_app.config['TESTING'])
    duplicate_pin_headers, duplicate_pin_results = db.get_duplicate_pins(db_conn)
    missing_pin_headers, missing_pin_results = db.get_missing_pins(db_conn)
    print_all(f'record_{request.method}')
    return render_template('auth/record.html', error=error, 
        duplicate_pin_headers=duplicate_pin_headers, 
        duplicate_pin_results=duplicate_pin_results, 
        missing_pin_headers=missing_pin_headers, 
        missing_pin_results=missing_pin_results, 
        testing=current_app.config['TESTING']
        )
