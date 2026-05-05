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

def check_credentials(request: Request):
    '''
    return username if user is logged in
    if not logged in return None
    '''
    query_username = request.query_params.get('username')
    query_password = request.query_params.get('password')
    print('query_username=', query_username)
    print('query_password=', query_password)

    cookie_username = request.cookies.get('username')
    cookie_password = request.cookies.get('password')
    print('cookie_username=', cookie_username)
    print('cookie_password=', cookie_password)

    username = cookie_username
    password = cookie_password

    # should connect to the db
    # and check if username/password in the users table
    if username == 'Trump' and password == '12345':
        print(f'logged in as {username}')
        return True
    else:
        print('not logged in')
        return False

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    # create response
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'is_logged_in': check_credentials(request),
            'username': check_credentials(request),
        },
    )

@app.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    response = templates.TemplateResponse(
        request=request,
        name='login.html',
        context={
            'is_logged_in': check_credentials(request),
            'username': check_credentials(request),
        },
    )
    response.set_cookie(key='username', value=request.query_params.get('username'))
    response.set_cookie(key='password', value=request.query_params.get('password'))
    return response

@app.get('/logout', response_class=HTMLResponse)
async def logout(request: Request):
    response = templates.TemplateResponse(
        request=request,
        name='logout.html',
        context={
            'is_logged_in': check_credentials(request),
            'username': check_credentials(request),
        },
    )
    response.delete_cookie(key='username')
    response.delete_cookie(key='password')
    return response

@app.get('/create_message', response_class=HTMLResponse)
async def create_message(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='create_message.html',
        context={
            'is_logged_in': check_credentials(request),
            'username': check_credentials(request),
        },
    )

@app.get('/create_user', response_class=HTMLResponse)
async def create_user(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='create_user.html',
        context={
            'is_logged_in': check_credentials(request),
            'username': check_credentials(request),
        },
    )

if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8080, reload=True)
