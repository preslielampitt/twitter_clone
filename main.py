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
    url_pattern = r'(https?://[^\s]+)'

    linked_text = re.sub(
        url_pattern,
        r'<a href="\1">\1</a>',
        str(escaped_text)
    )

    return Markup(linked_text)

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    username = check_credentials(request)
    messages = []

    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    sql = """
    SELECT messages.id, messages.message, messages.created_at, users.username, users.age, messages.last_edited_at
    FROM messages
    JOIN users ON messages.sender_id = users.id
    ORDER BY messages.created_at DESC;
    """
    cur.execute(sql)
    for row in cur.fetchall():
        message = {
            'id': row[0],
            'text': linkify_message(row[1]),
            'timestamp': row[2],
            'username': row[3],
            'age': row[4],
            'last_edited_at': row[5],
            'image_url': 'https://robohash.org/' + quote(row[3]) + '?set=set1&size=80x80',
        }
        messages.append(message)
    con.close()

    # create response
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'is_logged_in': username is not None,
            'username': username,
            'messages': messages,
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
        if password != password_again:
            error = 'Passwords do not match.'
        else:
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

@app.get('/api/messages')
async def api_messages():
    con = sqlite3.connect('twitter_clone.db')
    cur = con.cursor()
    cur.execute(
        '''
        SELECT messages.id, messages.message, messages.created_at, users.username, users.age
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
        })

    con.close()
    return JSONResponse(messages)

if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8080, reload=True)
