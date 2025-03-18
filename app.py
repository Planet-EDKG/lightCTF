from flask import Flask
from config import Config
from database import init_db, add_user, refresh_database
from routes import configure_routes
import sqlite3

app = Flask(__name__)
app.config.from_object(Config)

# Initialisiere die Datenbank
init_db()
refresh_database()

# Standardbenutzer erstellen, falls Datenbank leer ist
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM users')
user_count = c.fetchone()[0]
conn.close()

if user_count == 0:
    add_user('admin', 'adminpass', 'Admin')
    add_user('user', 'userpass', 'Player')

# Routen konfigurieren
configure_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
