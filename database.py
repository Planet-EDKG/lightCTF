import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            score INT DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            question TEXT NOT NULL,
            solution TEXT NOT NULL,
            points INT NOT NULL
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

def save_challenge(name, question, solution, points):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO questions (name, question, solution, points) VALUES (?, ?, ?, ?)',
              (name, question, solution, points))
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