from flask import render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import os
import json
import sqlite3
from database import add_user, get_all_challenges, save_challenge, get_entire_points
from helpers import allowed_file

def configure_routes(app):

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

    @app.route('/admin')
    def admin_dashboard():
        if 'role' in session and session['role'] == 'Admin':
            return render_template('admin.html')  
        return redirect(url_for('login'))

    @app.route('/user')
    def user_dashboard():
        if 'role' in session and session['role'] == 'Player':
            return render_template('user.html')  
        return redirect(url_for('login'))

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
            flash('User successfully registered!', 'success')  
            return redirect(url_for('register')) 

        return render_template('register.html')

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

    @app.route('/export_challenges', methods=['GET'])
    def export_challenges():
        challenges = get_all_challenges()  
        challenges_list = [{"Name": c[0], "Question": c[1], "Solution": c[2], "Points": c[3]} for c in challenges]

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'challenges_export.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(challenges_list, f, ensure_ascii=False, indent=4)

        return send_file(file_path, as_attachment=True, download_name='challenges_export.json')

    @app.route('/add_challenge', methods=['GET', 'POST'])
    def add_challenge():
        if request.method == 'POST':
            if 'file' in request.files:
                file = request.files['file']
                if file.filename.endswith('.json'):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                    file.save(file_path)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        challenges = json.load(f)
                        for challenge in challenges:
                            save_challenge(challenge["Name"], challenge["Question"], challenge["Solution"], challenge["Points"])
                    flash('JSON file successfully imported!', 'success')
                    return redirect(url_for('add_challenge'))
                else:
                    flash('Please upload a valid JSON file!', 'danger')
            else:
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
