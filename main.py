'''
Starts a hello world webserver.
'''

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import sqlite3

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

# Internal Server Error:
# always means a python error inside of the function that corresponds to the route
# or "page" that you were connecting to in firefox
@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    is_logged_in = True

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
            'text': row[0],
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
            'is_logged_in': is_logged_in,
            'messages': messages,
        },
    )

@app.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    is_logged_in='True'
    return templates.TemplateResponse(
        request=request,
        name='login.html',
        context={
            'is_logged_in': is_logged_in
        },
    )

@app.get('/logout', response_class=HTMLResponse)
async def logout(request: Request):
    is_logged_in='False'
    return templates.TemplateResponse(
        request=request,
        name='logout.html',
        context={
            'is_logged_in': is_logged_in
        },
    )

@app.get('/create_message', response_class=HTMLResponse)
async def create_message(request: Request):
    is_logged_in='True'
    return templates.TemplateResponse(
        request=request,
        name='create_message.html',
        context={
            'is_logged_in': is_logged_in
        },
    )

@app.get('/create_user', response_class=HTMLResponse)
async def create_user(request: Request):
    is_logged_in='True'
    return templates.TemplateResponse(
        request=request,
        name='create_user.html',
        context={
            'is_logged_in': is_logged_in
        },
    )

if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8080, reload=True)
