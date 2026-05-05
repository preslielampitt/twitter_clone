'''
Starts a hello world webserver.
'''

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import sqlite3
import re
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
    SELECT messages.message, messages.created_at, users.username, users.age
    FROM messages
    JOIN users ON messages.sender_id = users.id
    ORDER BY messages.created_at DESC;
    """
    cur.execute(sql)
    for row in cur.fetchall():
        message = {
            'text': linkify_message(row[0]),
            'timestamp': row[1],
            'username': row[2],
            'age': row[3],
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

if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8080, reload=True)
