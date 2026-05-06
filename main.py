'''
Starts a hello world webserver.
'''

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import sqlite3
import re
from urllib.parse import quote
from markupsafe import Markup, escape

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')
MESSAGES_PER_PAGE = 50
PROFILE_MESSAGE_LIMIT = 10
USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{3,30}$')

def check_credentials(request: Request):
    '''
    Return username if user is logged in.
    If not logged in, return None.
    '''
    cookie_username = request.cookies.get('username')
    cookie_password = request.cookies.get('password')

    if cookie_username is None or cookie_password is None:
        return None

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    sql = """
    SELECT username
    FROM users
    WHERE username = ? AND password = ?;
    """
    cur.execute(sql, (cookie_username, cookie_password))
    row = cur.fetchone()
    con.close()

    if row is None:
        return None
    return row[0]

def get_user_id(username):
    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    sql = """
    SELECT id
    FROM users
    WHERE username = ?;
    """
    cur.execute(sql, (username,))
    row = cur.fetchone()
    con.close()

    if row is None:
        return None
    return row[0]

def linkify_message(text):
    escaped_text = escape(text)
    link_pattern = r'(https?://[^\s]+)|(?<![\w/])@([A-Za-z0-9_]+)'

    def replace_link(match):
        if match.group(1):
            url = match.group(1)
            return f'<a href="{url}">{url}</a>'

        username = match.group(2)
        profile_url = '/profile?username=' + quote(username)
        return f'<a href="{profile_url}">@{username}</a>'

    linked_text = re.sub(link_pattern, replace_link, str(escaped_text))

    return Markup(linked_text)

def build_message(row):
    return {
        'id': row[0],
        'text': linkify_message(row[1]),
        'timestamp': row[2],
        'username': row[3],
        'age': row[4],
        'last_edited_at': row[5],
        'image_url': 'https://robohash.org/' + quote(row[3]) + '?set=set1&size=80x80',
        'replies': [],
    }

def get_offset(request: Request):
    offset = request.query_params.get('offset', '0')
    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    if offset < 0:
        offset = 0
    return offset

def validate_new_account(username, password, password_again, age):
    if username is None or password is None or password_again is None:
        return None

    if not USERNAME_PATTERN.fullmatch(username):
        return 'Username must be 3-30 characters and use only letters, numbers, and underscores.'

    if password == '':
        return 'Password cannot be blank.'

    if password != password_again:
        return 'Passwords do not match.'

    if age not in (None, ''):
        try:
            age_number = int(age)
        except ValueError:
            return 'Age must be a number.'

        if age_number < 0 or age_number > 130:
            return 'Age must be between 0 and 130.'

    return None

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    username = check_credentials(request)
    messages = []
    offset = get_offset(request)

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM messages WHERE parent_id IS NULL;')
    total_messages = cur.fetchone()[0]

    sql = """
    SELECT messages.id, messages.message, messages.created_at, users.username, users.age, messages.last_edited_at
    FROM messages
    JOIN users ON messages.sender_id = users.id
    WHERE messages.parent_id IS NULL
    ORDER BY messages.created_at DESC
    LIMIT ? OFFSET ?;
    """
    cur.execute(sql, (MESSAGES_PER_PAGE, offset))
    message_ids = []
    for row in cur.fetchall():
        message = build_message(row)
        messages.append(message)
        message_ids.append(message['id'])

    if message_ids:
        placeholders = ','.join(['?'] * len(message_ids))
        sql = f"""
        SELECT messages.id, messages.message, messages.created_at, users.username, users.age, messages.last_edited_at, messages.parent_id
        FROM messages
        JOIN users ON messages.sender_id = users.id
        WHERE messages.parent_id IN ({placeholders})
        ORDER BY messages.created_at ASC;
        """
        cur.execute(sql, message_ids)
        messages_by_id = {}
        for message in messages:
            messages_by_id[message['id']] = message
        for row in cur.fetchall():
            reply = build_message(row[:6])
            parent_id = row[6]
            if parent_id in messages_by_id:
                messages_by_id[parent_id]['replies'].append(reply)
    con.close()

    # create response
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'is_logged_in': username is not None,
            'username': username,
            'messages': messages,
            'previous_offset': max(offset - MESSAGES_PER_PAGE, 0),
            'next_offset': offset + MESSAGES_PER_PAGE,
            'has_previous': offset > 0,
            'has_next': offset + MESSAGES_PER_PAGE < total_messages,
        },
    )

@app.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    username = request.query_params.get('username')
    password = request.query_params.get('password')
    error = None

    if username is not None and password is not None:
        con = sqlite3.connect('twitter_clone.db')
        cur = con.cursor()
        sql = """
        SELECT id
        FROM users
        WHERE username = ? AND password = ?;
        """
        cur.execute(sql, (username, password))
        row = cur.fetchone()
        con.close()

        if row is not None:
            response = RedirectResponse(url='/', status_code=302)
            response.set_cookie(key='username', value=username)
            response.set_cookie(key='password', value=password)
            return response

        error = 'Incorrect username or password.'

    current_username = check_credentials(request)
    return templates.TemplateResponse(
        request=request,
        name='login.html',
        context={
            'is_logged_in': current_username is not None,
            'username': current_username,
            'error': error,
        },
    )

@app.get('/logout', response_class=HTMLResponse)
async def logout(request: Request):
    response = templates.TemplateResponse(
        request=request,
        name='logout.html',
        context={
            'is_logged_in': False,
            'username': None,
        },
    )
    response.delete_cookie(key='username')
    response.delete_cookie(key='password')
    return response

@app.get('/create_message', response_class=HTMLResponse)
async def create_message(request: Request):
    username = check_credentials(request)
    if username is None:
        return RedirectResponse(url='/login', status_code=302)

    message_text = request.query_params.get('message')
    error = None

    if message_text is not None:
        if message_text == '':
            error = 'Message cannot be blank.'
        else:
            user_id = get_user_id(username)
            con = sqlite3.connect('twitter_clone.db')
            cur = con.cursor()
            sql = """
            INSERT INTO messages (sender_id, message)
            VALUES (?, ?);
            """
            cur.execute(sql, (user_id, message_text))
            con.commit()
            con.close()
            return RedirectResponse(url='/', status_code=302)

    return templates.TemplateResponse(
        request=request,
        name='create_message.html',
        context={
            'is_logged_in': True,
            'username': username,
            'error': error,
        },
    )

@app.get('/create_user', response_class=HTMLResponse)
async def create_user(request: Request):
    current_username = check_credentials(request)
    if current_username is not None:
        return RedirectResponse(url='/', status_code=302)

    username = request.query_params.get('username')
    password = request.query_params.get('password')
    password_again = request.query_params.get('password_again')
    age = request.query_params.get('age')
    error = None

    if username is not None and password is not None and password_again is not None:
        error = validate_new_account(username, password, password_again, age)
        if error is None:
            con = sqlite3.connect('twitter_clone.db')
            try:
                cur = con.cursor()
                sql = """
                INSERT INTO users (username, password, age)
                VALUES (?, ?, ?);
                """
                cur.execute(sql, (username, password, age))
                con.commit()

                response = RedirectResponse(url='/', status_code=302)
                response.set_cookie(key='username', value=username)
                response.set_cookie(key='password', value=password)
                return response
            except sqlite3.IntegrityError:
                error = 'That username already exists.'
            finally:
                con.close()

    return templates.TemplateResponse(
        request=request,
        name='create_user.html',
        context={
            'is_logged_in': False,
            'username': None,
            'error': error,
        },
    )

@app.get('/delete_message')
async def delete_message(request: Request):
    username = check_credentials(request)
    if username is None:
        return RedirectResponse(url='/login', status_code=302)

    message_id = request.query_params.get('id')
    user_id = get_user_id(username)

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    cur.execute(
        '''
        DELETE FROM messages
        WHERE parent_id = ? AND ? = (
            SELECT sender_id
            FROM messages
            WHERE id = ?
        );
        ''',
        (message_id, user_id, message_id)
    )
    cur.execute(
        '''
        DELETE FROM messages
        WHERE id = ? AND sender_id = ?;
        ''',
        (message_id, user_id)
    )
    con.commit()
    con.close()

    return RedirectResponse(url='/', status_code=302)

@app.get('/edit_message', response_class=HTMLResponse)
async def edit_message(request: Request):
    username = check_credentials(request)
    if username is None:
        return RedirectResponse(url='/login', status_code=302)

    message_id = request.query_params.get('id')
    new_message = request.query_params.get('message')
    user_id = get_user_id(username)

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()

    if new_message is not None:
        cur.execute(
            '''
            UPDATE messages
            SET message = ?, last_edited_at = current_timestamp
            WHERE id = ? AND sender_id = ?;
            ''',
            (new_message, message_id, user_id)
        )
        con.commit()
        con.close()
        return RedirectResponse(url='/', status_code=302)

    cur.execute(
        '''
        SELECT message
        FROM messages
        WHERE id = ? AND sender_id = ?;
        ''',
        (message_id, user_id)
    )
    row = cur.fetchone()
    con.close()

    if row is None:
        return RedirectResponse(url='/', status_code=302)

    return templates.TemplateResponse(
        request=request,
        name='edit_message.html',
        context={
            'is_logged_in': True,
            'message_id': message_id,
            'message_text': row[0],
        },
    )

@app.get('/reply_message', response_class=HTMLResponse)
async def reply_message(request: Request):
    username = check_credentials(request)
    if username is None:
        return RedirectResponse(url='/login', status_code=302)

    parent_id = request.query_params.get('id')
    reply_text = request.query_params.get('message')
    error = None

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    cur.execute(
        '''
        SELECT messages.id, messages.message, messages.created_at, users.username, users.age, messages.last_edited_at
        FROM messages
        JOIN users ON messages.sender_id = users.id
        WHERE messages.id = ? AND messages.parent_id IS NULL;
        ''',
        (parent_id,)
    )
    parent_row = cur.fetchone()

    if parent_row is None:
        con.close()
        return RedirectResponse(url='/', status_code=302)

    if reply_text is not None:
        if reply_text == '':
            error = 'Reply cannot be blank.'
        else:
            user_id = get_user_id(username)
            cur.execute(
                '''
                INSERT INTO messages (sender_id, message, parent_id)
                VALUES (?, ?, ?);
                ''',
                (user_id, reply_text, parent_id)
            )
            con.commit()
            con.close()
            return RedirectResponse(url='/', status_code=302)

    con.close()
    return templates.TemplateResponse(
        request=request,
        name='reply_message.html',
        context={
            'is_logged_in': True,
            'username': username,
            'parent_message': build_message(parent_row),
            'parent_id': parent_id,
            'error': error,
        },
    )

@app.get('/delete_user')
async def delete_user(request: Request):
    username = check_credentials(request)
    if username is None:
        return RedirectResponse(url='/login', status_code=302)

    user_id = get_user_id(username)

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()

    cur.execute('DELETE FROM messages WHERE sender_id = ?;', (user_id,))
    cur.execute('DELETE FROM users WHERE id = ?;', (user_id,))

    con.commit()
    con.close()

    response = RedirectResponse(url='/', status_code=302)
    response.delete_cookie(key='username')
    response.delete_cookie(key='password')
    return response

@app.get('/change_password', response_class=HTMLResponse)
async def change_password(request: Request):
    username = check_credentials(request)
    if username is None:
        return RedirectResponse(url='/login', status_code=302)

    old_password = request.query_params.get('old_password')
    new_password = request.query_params.get('new_password')
    new_password_again = request.query_params.get('new_password_again')
    error = None

    if old_password is not None and new_password is not None and new_password_again is not None:
        if new_password != new_password_again:
            error = 'New passwords do not match.'
        elif new_password == '':
            error = 'New password cannot be blank.'
        else:
            con = sqlite3.connect('twitter_clone.db')
            cur = con.cursor()
            sql = """
            UPDATE users
            SET password = ?
            WHERE username = ? AND password = ?;
            """
            cur.execute(sql, (new_password, username, old_password))
            con.commit()
            changed_rows = cur.rowcount
            con.close()

            if changed_rows == 0:
                error = 'Old password is incorrect.'
            else:
                response = RedirectResponse(url='/', status_code=302)
                response.set_cookie(key='username', value=username)
                response.set_cookie(key='password', value=new_password)
                return response

    return templates.TemplateResponse(
        request=request,
        name='change_password.html',
        context={
            'is_logged_in': True,
            'username': username,
            'error': error,
        },
    )

@app.get('/profile', response_class=HTMLResponse)
async def profile(request: Request):
    current_username = check_credentials(request)
    profile_username = request.query_params.get('username')

    if profile_username is None:
        if current_username is None:
            return RedirectResponse(url='/login', status_code=302)
        profile_username = current_username

    new_description = request.query_params.get('description')
    error = None
    success = None
    is_owner = current_username == profile_username

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()

    if new_description is not None:
        if not is_owner:
            error = 'You can only edit your own profile.'
        else:
            sql = """
            UPDATE users
            SET description = ?
            WHERE username = ?;
            """
            cur.execute(sql, (new_description, profile_username))
            con.commit()
            success = 'Profile updated.'

    sql = """
    SELECT username, age, description
    FROM users
    WHERE username = ?;
    """
    cur.execute(sql, (profile_username,))
    user_row = cur.fetchone()

    if user_row is None:
        con.close()
        return RedirectResponse(url='/', status_code=302)

    sql = """
    SELECT id, message, created_at, last_edited_at
    FROM messages
    WHERE sender_id = ?
    ORDER BY created_at DESC
    LIMIT ?;
    """
    cur.execute(sql, (get_user_id(profile_username), PROFILE_MESSAGE_LIMIT))

    recent_messages = []
    for row in cur.fetchall():
        recent_messages.append({
            'id': row[0],
            'text': linkify_message(row[1]),
            'timestamp': row[2],
            'last_edited_at': row[3],
        })
    con.close()

    return templates.TemplateResponse(
        request=request,
        name='profile.html',
        context={
            'is_logged_in': current_username is not None,
            'username': current_username,
            'profile_username': user_row[0],
            'profile_age': user_row[1],
            'profile_description': user_row[2],
            'profile_image_url': 'https://robohash.org/' + quote(user_row[0]) + '?set=set1&size=120x120',
            'recent_messages': recent_messages,
            'is_owner': is_owner,
            'error': error,
            'success': success,
        },
    )

@app.get('/api/messages')
async def api_messages():
    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    cur.execute(
        '''
        SELECT messages.id, messages.message, messages.created_at, users.username, users.age, messages.parent_id
        FROM messages
        JOIN users ON messages.sender_id = users.id
        ORDER BY messages.created_at DESC;
        '''
    )

    messages = []
    for row in cur.fetchall():
        messages.append({
            'id': row[0],
            'text': row[1],
            'created_at': row[2],
            'username': row[3],
            'age': row[4],
            'parent_id': row[5],
        })

    con.close()
    return JSONResponse(messages)

if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8080, reload=True)
