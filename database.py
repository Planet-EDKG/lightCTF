import sqlite3
import json  # Add this import at the top of the file

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            score INT DEFAULT 0,
            blackmarket_points INT DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            question TEXT NOT NULL,
            solution TEXT NOT NULL,
            kategory TEXT NOT NULL,
            options TEXT,
            points INT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS help (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hint TEXT NOT NULL,
            costs INTEGER NOT NULL,
            challenge_id TEXT NOT NULL,
            FOREIGN KEY (challenge_id) REFERENCES questions(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchased_hints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            challenge_id INTEGER NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (challenge_id) REFERENCES questions(id),
            UNIQUE(username, challenge_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS correct_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            challenge_id INTEGER,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (challenge_id) REFERENCES questions(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS answered_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            challenge_id INTEGER,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (challenge_id) REFERENCES questions(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS blackmarket (
            id INTEGER PRIMARY KEY, 
            name TEXT, 
            costs INTEGER, 
            image TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchased_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (item_id) REFERENCES blackmarket(id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password, role):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
    conn.commit()
    conn.close()

def get_all_challenges():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT name, question, solution, points FROM questions')
    challenges = c.fetchall()
    conn.close()
    return challenges

def save_challenge(name, question, solution, kategory, options, points):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Convert options list to JSON string if it exists
    options_json = json.dumps(options) if options else None
    
    c.execute('INSERT INTO questions (name, question, solution, kategory, options, points) VALUES (?, ?, ?, ?, ?, ?)',
              (name, question, solution, kategory, options_json, points))
    conn.commit()
    conn.close()

def get_entire_points():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT SUM(points) FROM questions')
    points = c.fetchone()[0]
    conn.close()
    return points

def refresh_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM questions;')
    conn.commit()
    conn.close()
    
def update_user_points(username, points):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET score = score + ?, blackmarket_points = blackmarket_points + ? WHERE username = ?', (points, points, username))
    conn.commit()
    conn.close()

def buy_blackmarket_item(username, item_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT costs, image FROM blackmarket WHERE id = ?', (item_id,))
    item = c.fetchone()
    
    if not item:
        return "Item not found"
    
    cost, image = item
    c.execute('SELECT blackmarket_points FROM users WHERE username = ?', (username,))
    user_points = c.fetchone()[0]
    
    if user_points < cost:
        return "Not enough points"
    
    c.execute('UPDATE users SET blackmarket_points = blackmarket_points - ? WHERE username = ?', (cost, username))
    conn.commit()
    conn.close()
    
    return f"Download available: {image}"

def get_challenge_options(challenge_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT options FROM questions WHERE id = ?', (challenge_id,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        return json.loads(result[0])
    return []