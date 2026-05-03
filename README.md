# Twitter Clone

Twitter Clone functions similarly to Twitter (now X). The home page displays messages, beginning with the newest, from different users with its timestamp, author, and the author's age.

## How to Run

Set up the virtual environment and install the packages:

```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn jinja2
```

Create the database:

```bash
python3 db_create.py
```

Start the server:

```bash
python3 main.py
```

Open the app in a browser:

```bash
http://127.0.0.1:8080
```

## Home Page Screenshot

![Screenshot of the home page](static/home_screenshot.png)
