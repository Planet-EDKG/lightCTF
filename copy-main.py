import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import os
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "json", "py", "txt"}

# Initialize database
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
        CREATE TABLE IF NOT EXISTS correct_answers  (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            challenge_id INTEGER,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (challenge_id) REFERENCES questions(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS answered_questions  (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            challenge_id INTEGER,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (challenge_id) REFERENCES questions(id)
        )
    ''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS blackmarket (
            id INTEGER PRIMARY KEY, 
            name TEXT, 
            costs INTEGER, 
            image TEXT
            )
    ''')
    conn.commit()
    conn.close()

def refresh_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM users;')
    c.execute('DELETE FROM questions;')
    conn.commit()
    conn.close()

# Add user to database
def add_user(username, password, role):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
    conn.commit()
    conn.close()

# Fetch all challenges from DB
def get_all_challenges():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT name, question, solution, points FROM questions')
    challenges = c.fetchall()
    conn.close()
    return challenges

# Save challenge to database (for import)
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

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and user[2] == password:
            session['username'] = user[1]
            session['role'] = user[3]

            if user[3] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user[3] == 'Player':
                return redirect(url_for('user_dashboard'))
        else:
            return 'Invalid login credentials', 401

    return render_template('login.html')

# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'Admin':
        return render_template('admin.html')  
    return redirect(url_for('login'))

# User Dashboard
@app.route('/user')
def user_dashboard():
    if 'role' in session and session['role'] == 'Player':
        return render_template('user.html')  
    return redirect(url_for('login'))

@app.route('/challenges', methods=['GET', 'POST'])
def play_game():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, name, question, solution, points FROM questions')
    challenges = c.fetchall()

    answered_questions = []
    correct_answers = []
    
    if 'username' in session:
        username = session['username']
        c.execute('SELECT challenge_id FROM answered_questions WHERE username = ?', (username,))
        answered_questions = [row[0] for row in c.fetchall()]

        c.execute('SELECT challenge_id FROM correct_answers WHERE username = ?', (username,))
        correct_answers = [row[0] for row in c.fetchall()]

    if request.method == 'POST':
        challenge_id = int(request.form['challenge_id'])
        user_answer = request.form.get(f'answer_{challenge_id}', '').strip()
        c.execute('SELECT solution, points FROM questions WHERE id = ?', (challenge_id,))
        challenge = c.fetchone()

        if challenge:
            correct_solution, points = challenge

            if challenge_id in correct_answers:
                flash('You have already answered this question correctly!', 'info')
            else:
                if user_answer.lower() == correct_solution.lower():
                    c.execute('UPDATE users SET score = score + ? WHERE username = ?', (points, username))
                    c.execute('INSERT INTO correct_answers (username, challenge_id) VALUES (?, ?)', (username, challenge_id))
                    flash(f'Correct answer! You earned {points} points.', 'success')
                else:
                    flash('Wrong answer! Try again.', 'danger')

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

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        add_user(username, password, role)
        flash('User successfully registered!', 'success')  
        return redirect(url_for('register')) 

    return render_template('register.html')

# Function to export challenges as JSON
@app.route('/export_challenges', methods=['GET'])
def export_challenges():
    challenges = get_all_challenges()  
    challenges_list = []
    
    # Convert challenges into a JSON-compatible list
    for challenge in challenges:
        challenges_list.append({
            "Name": challenge[0],
            "Question": challenge[1],
            "Solution": challenge[2],
            "Points": challenge[3]
        })
    # Create a JSON file and save it
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'challenges_export.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(challenges_list, f, ensure_ascii=False, indent=4)

    return send_file(file_path, as_attachment=True, download_name='challenges_export.json')

@app.route('/add_challenge', methods=['GET', 'POST'])
def add_challenge():
    if request.method == 'POST':
        if 'file' in request.files:  # Check if a file was uploaded
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
                flash('JSON file successfully imported!', 'success')
                return redirect(url_for('add_challenge'))
            else:
                flash('Please upload a valid JSON file!', 'danger')

        else:
            # Save manual input
            name = request.form['Name']
            question = request.form['Question']
            solution = request.form['Solution']
            points = request.form['Points']
            save_challenge(name, question, solution, points)
            flash('Question successfully added!', 'success')  
            return redirect(url_for('add_challenge')) 

    return render_template('add_challenge.html')

@app.route('/scoreboard', methods=['GET'])
def scoreboard():
    points = get_entire_points()

    if 'username' not in session:
        return redirect(url_for('login')) 

    username = session['username']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('SELECT username, score FROM users ORDER BY score DESC')
    users = c.fetchall()

    c.execute('SELECT role FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()

    users = [user for user in users if user[0].lower() != "admin"]

    if user:
        role = user[0]  
        if role == 'Admin':
            return render_template('scoreboard_admin.html', users=users, points=points)
        elif role == 'Player':
            return render_template('scoreboard_user.html', users=users, points=points)

@app.route("/add_blackmarket", methods=["GET", "POST"])
def add_blackmarket():
    if request.method == "POST":
        name = request.form["Name"]
        costs = request.form["Costs"]
        file = request.files["file"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("INSERT INTO blackmarket (name, costs, image) VALUES (?, ?, ?)", (name, costs, filename))
            conn.commit()
            conn.close()

            flash("Item successfully added!", "success")
            return redirect(url_for("add_blackmarket"))

    return render_template("add_blackmarket.html")


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