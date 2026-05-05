#!/usr/bin/python3
'''
Create a database for the Twitter project.
'''

# sqlite3 is built in python3, no need to pip install
import sqlite3
import random

# process command line arguments
import argparse
parser = argparse.ArgumentParser(description='Create a database for the twitter project')
parser.add_argument('--db_file', default='twitter_clone.db')
args = parser.parse_args()

# connect to the database
con = sqlite3.connect(args.db_file)   # con, conn = connection; always exactly 1 of these variables per python project
cur = con.cursor()                    # cur = cursor; for our purposes, exactly 1 of these per python file

# create the users table
sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    age INTEGER
);
'''
cur.execute(sql)     # cur.execute() actually runs the SQL code
con.commit()         # "commit" means "save" in SQL terminology; not always required, but never wrong

# insert some dummy data
cur.execute('''insert into users (username, password, age) values ('Trump', 'Trump', 78);''')
cur.execute('''insert into users (username, password, age) values (\'Biden\', \'Biden\', 81);''')
cur.execute('''insert into users (username, password, age) values ('Evan', 'correct horse battery staple', 7);''')
cur.execute('''insert into users (username, password, age) values ('Isaac', 'soccer', 4);''')
cur.execute('''insert into users (username, password, age) values ('Aaron', 'guaguagua', 3);''')
cur.execute('''insert into users (username, password, age) values ('Aurelia', '', 1);''')
cur.execute('''insert into users (username, password, age) values ('Mike', '524euTjrWm6uK2C5iw8mC6aNgX1JI78o', 35);''')
cur.execute('''insert into users (username, password) values ('Kristen', 'Possible-Rich-Absolute-Battle');''')
con.commit()

# create the messages table
sql = '''
create table messages (
    id integer primary key,
    sender_id integer not null,
    message text not null,
    created_at timestamp not null default current_timestamp,
    last_edited_at timestamp
    );
'''
cur.execute(sql)
con.commit()

# insert random users and messages
topics = [
    'SQLite', 'FastAPI', 'Python', 'HTML', 'CSS',
    'databases', 'web apps', 'cookies', 'templates', 'routes'
]

activities = [
    'learning about', 'debugging', 'building', 'testing',
    'reading about', 'experimenting with', 'improving'
]

opinions = [
    'is starting to make sense',
    'is harder than I expected',
    'is actually pretty fun',
    'is useful for this project',
    'works better after some practice',
    'is something I want to understand better'
]

websites = [
    'https://www.python.org',
    'https://fastapi.tiangolo.com',
    'https://www.sqlite.org',
    'https://developer.mozilla.org'
]

templates = [
    'I spent some time {activity} {topic}, and it {opinion}.',
    'Today I worked on {topic}. It {opinion}.',
    'I found this helpful while learning {topic}: {website}',
    'My current project uses {topic}, and it {opinion}.',
    'I had a bug with {topic}, but it {opinion} now.',
    'I am still {activity} {topic}, but it {opinion}.',
    'This message has a single quote \' and a double quote " so I can test escaping.',
]

for user_number in range(200):
    username = f'user{user_number}'
    password = f'password{user_number}'
    age = random.randint(13, 90)

    cur.execute(
        '''
        INSERT INTO users (username, password, age)
        VALUES (?, ?, ?);
        ''',
        (username, password, age)
    )

    user_id = cur.lastrowid

    for message_number in range(200):
        template = random.choice(templates)
        message = template.format(
            activity=random.choice(activities),
            topic=random.choice(topics),
            opinion=random.choice(opinions),
            website=random.choice(websites),
        )

        cur.execute(
            '''
            INSERT INTO messages (sender_id, message)
            VALUES (?, ?);
            ''',
            (user_id, message)
        )

con.commit()
