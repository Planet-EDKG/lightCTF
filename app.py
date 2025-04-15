from flask import Flask
from config import Config
from database import init_db, add_user, refresh_database
from routes import configure_routes
import sqlite3
import os

app = Flask(__name__)
app.config.from_object(Config)

init_db()
refresh_database()

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM users')
user_count = c.fetchone()[0]
conn.close()

if user_count == 0:
    add_user('admin', 'adminpass', 'Admin')
    add_user('user', 'userpass', 'Player')

configure_routes(app)

if os.environ.get('RENDER'):
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)