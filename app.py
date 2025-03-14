import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os
import json

app = Flask(__name__)
app.secret_key = 'dein_geheimes_schlüssel'

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Erstelle den Upload-Ordner falls nicht vorhanden
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Tabelle erstellen, falls sie noch nicht existiert
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
        CREATE TABLE IF NOT EXISTS correct_answers  (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            challenge_id INTEGER,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (challenge_id) REFERENCES challenges(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS answered_questions  (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            challenge_id INTEGER,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (challenge_id) REFERENCES challenges(id)
        )
    ''')
    conn.commit()
    conn.close()

def refresh_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        DELETE FROM users;
    ''')
    c.execute('''
        DELETE FROM questions;
    ''')
    conn.commit()
    conn.close()

# Benutzer zur Datenbank hinzufügen
def add_user(username, password, role):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Benutzer in die Datenbank einfügen (Passwort im Klartext)
    c.execute('''
        INSERT INTO users (username, password, role) 
        VALUES (?, ?, ?)
    ''', (username, password, role))
    
    conn.commit()
    conn.close()

# Funktion, um Challenges aus der DB zu holen
def get_all_challenges():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT name, question, solution, points FROM questions')
    challenges = c.fetchall()
    conn.close()
    return challenges

# Funktion, um Challenges zu speichern (Für Import)
def save_challenge(name, question, solution, points):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO questions (name, question, solution, points) VALUES (?, ?, ?, ?)',
              (name, question, solution, points))
    conn.commit()
    conn.close()

# Anmeldung
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Überprüfen, ob der Benutzer existiert und das Passwort korrekt ist
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and user[2] == password:  # user[2] ist das Passwort (Klartext)
            # Benutzerrolle in der Session speichern
            session['username'] = user[1]
            session['role'] = user[3]

            # Nach erfolgreichem Login auf das Dashboard weiterleiten
            if user[3] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user[3] == 'Player':
                return redirect(url_for('user_dashboard'))
        else:
            return 'Ungültige Anmeldedaten', 401

    return render_template('login.html')

# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'Admin':
        return render_template('admin.html')  
    return redirect(url_for('login'))

# Benutzer Dashboard
@app.route('/user')
def user_dashboard():
    if 'role' in session and session['role'] == 'Player':
        return render_template('user.html')  
    return redirect(url_for('login'))

@app.route('/challenges', methods=['GET', 'POST'])
def play_game():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Alle Challenges abrufen
    c.execute('SELECT id, name, question, solution, points FROM questions')
    challenges = c.fetchall()

    # Beantwortete und korrekt beantwortete Fragen abrufen
    answered_questions = []
    correct_answers = []
    
    if 'username' in session:
        username = session['username']

        # Welche Fragen hat der User beantwortet?
        c.execute('SELECT challenge_id FROM answered_questions WHERE username = ?', (username,))
        answered_questions = [row[0] for row in c.fetchall()]

        # Welche Fragen hat der User bereits korrekt beantwortet?
        c.execute('SELECT challenge_id FROM correct_answers WHERE username = ?', (username,))
        correct_answers = [row[0] for row in c.fetchall()]

    if request.method == 'POST':
        challenge_id = int(request.form['challenge_id'])
        user_answer = request.form.get(f'answer_{challenge_id}', '').strip()

        # Richtige Lösung abrufen
        c.execute('SELECT solution, points FROM questions WHERE id = ?', (challenge_id,))
        challenge = c.fetchone()

        if challenge:
            correct_solution, points = challenge

            # Falls die Frage bereits korrekt beantwortet wurde, blockieren
            if challenge_id in correct_answers:
                flash('Diese Frage hast du bereits richtig beantwortet!', 'info')
            else:
                if user_answer.lower() == correct_solution.lower():  # Antwort vergleichen
                    c.execute('UPDATE users SET score = score + ? WHERE username = ?', (points, username))
                    c.execute('INSERT INTO correct_answers (username, challenge_id) VALUES (?, ?)', (username, challenge_id))
                    flash(f'Richtige Antwort! {points} Punkte erhalten.', 'success')
                else:
                    flash('Falsche Antwort! Versuch es erneut.', 'danger')

                # Speichert, dass der User diese Frage beantwortet hat
                if challenge_id not in answered_questions:
                    c.execute('INSERT INTO answered_questions (username, challenge_id) VALUES (?, ?)', (username, challenge_id))

            conn.commit()
        return redirect(url_for('play_game'))

    conn.close()
    return render_template('challenges.html', challenges=challenges, answered_questions=answered_questions, correct_answers=correct_answers)

# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        add_user(username, password, role)
        flash('Benutzer wurde erfolgreich registriert!', 'success')  
        return redirect(url_for('register')) 

    return render_template('register.html')

# Funktion zum Export der Challenges als JSON
@app.route('/export_challenges', methods=['GET'])
def export_challenges():
    challenges = get_all_challenges()  
    challenges_list = []
    
    # Umwandeln der Challenges in eine JSON-kompatible Liste
    for challenge in challenges:
        challenges_list.append({
            "Name": challenge[0],
            "Question": challenge[1],
            "Solution": challenge[2],
            "Points": challenge[3]
        })
    # Erstelle eine JSON-Datei und speichere sie
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'challenges_export.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(challenges_list, f, ensure_ascii=False, indent=4)

    return send_file(file_path, as_attachment=True, download_name='challenges_export.json')

@app.route('/add_challenge', methods=['GET', 'POST'])
def add_challenge():
    if request.method == 'POST':
        if 'file' in request.files:  # Prüfen ob Datei hochgeladen wurde
            file = request.files['file']
            if file.filename.endswith('.json'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    challenges = json.load(f)
                    for challenge in challenges:
                        save_challenge(
                            challenge["Name"], 
                            challenge["Question"], 
                            challenge["Solution"], 
                            challenge["Points"]
                        )
                flash('JSON-Datei erfolgreich importiert!', 'success')
                return redirect(url_for('add_challenge'))
            else:
                flash('Bitte eine gültige JSON-Datei hochladen!', 'danger')

        else:
            # Manuelle Eingabe speichern
            name = request.form['Name']
            question = request.form['Question']
            solution = request.form['Solution']
            points = request.form['Points']
            save_challenge(name, question, solution, points)
            flash('Frage wurde erfolgreich hinzugefügt!', 'success')  
            return redirect(url_for('add_challenge')) 

    return render_template('add_challenge.html')


if __name__ == '__main__':
    init_db()
      
    #refresh_database()
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    user_count = c.fetchone()[0]
    conn.close()

    if user_count == 0:

        add_user('admin', 'adminpass', 'Admin')
        add_user('user', 'userpass', 'Player')

    app.run(debug=True)
