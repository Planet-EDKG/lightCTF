from flask import render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import os
import json
import sqlite3
from database import add_user, get_all_challenges, save_challenge, get_entire_points, buy_blackmarket_item, update_user_points
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
            
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT id, username FROM users WHERE role = "Player"')  
            players = c.fetchall() 
            
            return render_template('admin.html', players=players)  
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
                        update_user_points(username, points)
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
            
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name FROM questions')  
        challenges = c.fetchall() 
        return render_template('add_challenge.html', challenges=challenges)
    
    @app.route('/delete_challenge', methods=['POST'])
    def delete_challenge():
        if 'role' in session and session['role'] == 'Admin':
            challenge_id = request.form.get('challenge_id')

            if challenge_id:
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('DELETE FROM questions WHERE id = ?', (challenge_id,))
                conn.commit()
                conn.close()
                flash('Deleted Challenge!', 'success')
            else:
                flash('Please choose a Challenge', 'error')

        return redirect(url_for('add_challenge'))  
    
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

    @app.route('/black_market', methods=['GET'])
    def blackmarket():
        if 'username' not in session:
            return redirect(url_for('login'))
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name, costs, image FROM blackmarket')
        items = [{'id': row[0], 'name': row[1], 'costs': row[2], 'image': row[3]} for row in c.fetchall()]
        conn.close()
        
        return render_template('blackmarket.html', items=items)

    @app.route('/buy_blackmarket', methods=['POST'])
    def buy_blackmarket():
        if 'username' not in session:
            return redirect(url_for('login'))
        
        username = session['username']
        item_id = request.form['item_id']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT item_id FROM purchased_items WHERE username = ? AND item_id = ?', (username, item_id))
        already_purchased = c.fetchone()
        
        if already_purchased:
            flash("You have already purchased this item!", 'danger')
            return redirect(url_for('blackmarket'))
        
        result = buy_blackmarket_item(username, item_id)
        if result.startswith("Download available"):
            filename = result.split(": ")[1]
            
            c.execute('INSERT INTO purchased_items (username, item_id) VALUES (?, ?)', (username, item_id))
            conn.commit()
            conn.close()
            
            return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)
        else:
            flash(result, 'danger')
            conn.close()
            return redirect(url_for('blackmarket'))
        
    @app.route('/reset_game', methods=['POST'])
    def reset_game():
        if 'role' in session and session['role'] == 'Admin':
            conn = sqlite3.connect('users.db')
            c = conn.cursor()

            c.execute('DELETE FROM answered_questions')
            c.execute('DELETE FROM correct_answers')
            c.execute('DELETE FROM purchased_items')
            c.execute('UPDATE users SET score = 0')
            c.execute('UPDATE users SET blackmarket_points = 0')

            conn.commit()
            conn.close()

            flash('Game reset successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    @app.route('/reset_players', methods=['POST'])
    def reset_player():
        if 'role' in session and session['role'] == 'Admin':
            username = request.form.get('username')
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET score = 0 WHERE role = ?', ('Player',))
            c.execute('UPDATE users SET blackmarket_points = 0 WHERE role = ?', ('Player',))
            conn.commit()
            conn.close()

            flash(f'Reset Players successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    @app.route('/add_points', methods=['POST'])
    def add_points():
        if 'role' in session and session['role'] == 'Admin':
            id = request.form.get('username')
            points = request.form.get('points')

            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET blackmarket_points = blackmarket_points + ? WHERE id = ?', (points, id))
            c.execute('SELECT username FROM users WHERE id = ?', (id,))
            username = c.fetchone()[0]
            conn.commit()
            conn.close()

            flash(f'Added {points} points to {username} successfully!', 'success')
        return redirect(url_for('admin_dashboard'))