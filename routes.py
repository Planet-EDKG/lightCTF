from flask import render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import json
import sqlite3
from database import add_user, get_all_challenges, save_challenge, get_entire_points, buy_blackmarket_item, update_user_points
from helpers import allowed_file
import re
from difflib import SequenceMatcher

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

        c.execute('''
            SELECT q.id, q.name, q.question, q.solution, q.points, q.options,
                   h.hint, h.costs
            FROM questions q
            LEFT JOIN help h ON q.id = h.challenge_id
        ''')
        
        challenges_data = c.fetchall()
        challenges = []
        hints = {}
        
        for row in challenges_data:
            challenge_id = row[0]
            options = json.loads(row[5]) if row[5] else []  # Parse JSON options
            challenge = {
                'id': challenge_id,
                'name': row[1],
                'question': row[2],
                'solution': row[3],
                'points': row[4],
                'options': options
            }
            challenges.append(challenge)
            if row[6]:  # hint exists
                hints[str(challenge_id)] = {'hint': row[6], 'costs': row[7]}
        
        answered_questions = []
        correct_answers = []

        if 'username' in session:
            username = session['username']
            c.execute('SELECT challenge_id FROM answered_questions WHERE username = ?', (username,))
            answered_questions = [row[0] for row in c.fetchall()]

            c.execute('SELECT challenge_id FROM correct_answers WHERE username = ?', (username,))
            correct_answers = [row[0] for row in c.fetchall()]

            c.execute('''
            SELECT ph.challenge_id 
            FROM purchased_hints ph 
            WHERE ph.username = ?
            ''', (username,))
            purchased_hints = [row[0] for row in c.fetchall()]
        else:
            purchased_hints = []

        if request.method == 'POST':
            challenge_id = int(request.form['challenge_id'])
            user_answer = request.form.get(f'answer_{challenge_id}', '').strip()
            
            # Get challenge details including options
            c.execute('SELECT solution, points, options FROM questions WHERE id = ?', (challenge_id,))
            challenge = c.fetchone()

            if challenge and 'username' in session:
                correct_solution, points, options_json = challenge
                options = json.loads(options_json) if options_json else None
                username = session['username']

                if challenge_id in correct_answers:
                    flash('You have already answered this question correctly!', 'info')
                else:
                    # Check if it's a multiple choice question
                    if options:
                        is_correct = user_answer == correct_solution
                    else:
                        # For text questions, use the normalize function
                        normalized_user_answer = normalize_text(user_answer)
                        normalized_solution = normalize_text(correct_solution)
                        is_correct = normalized_user_answer == normalized_solution

                    if is_correct:
                        update_user_points(username, points)
                        c.execute('INSERT INTO correct_answers (username, challenge_id) VALUES (?, ?)', 
                                (username, challenge_id))
                        flash(f'Correct answer! You earned {points} points.', 'success')
                    else:
                        if not options:
                            similarity = SequenceMatcher(None, normalized_user_answer, normalized_solution).ratio()
                            if similarity > 0.8:
                                flash('Very close! Check your spelling and formatting.', 'warning')
                            else:
                                flash('Wrong answer! Try again.', 'error')
                        else:
                            flash('Wrong answer! Try again.', 'error')

                    if challenge_id not in answered_questions:
                        c.execute('INSERT INTO answered_questions (username, challenge_id) VALUES (?, ?)', 
                                (username, challenge_id))

                conn.commit()

        conn.close()
        return render_template('challenges.html', 
                             challenges=challenges, 
                             answered_questions=answered_questions, 
                             correct_answers=correct_answers,
                             hints=hints,
                             purchased_hints=purchased_hints)

    def normalize_text(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[-_]', ' ', text)
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text

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
        if 'role' not in session or session['role'] != 'Admin':
            return redirect(url_for('login'))

        if request.method == 'POST':
            if 'file' in request.files:
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
                                challenge["Kategory"],
                                challenge.get("Options", []),
                                challenge["Points"]
                            )
                    flash('JSON file successfully imported!', 'success')
                    return redirect(url_for('add_challenge'))
                else:
                    flash('Please upload a valid JSON file!', 'danger')
            else:
                name = request.form['Name']
                question = request.form['Question']
                kategory = request.form['QuestionType']
                points = request.form['Points']
                question_type = request.form['QuestionType']

                if question_type == 'multiple_choice':
                    # Handle multiple choice questions
                    options = request.form.getlist('Options[]')
                    solution = request.form['CorrectOption']
                    if not options or len(options) < 2:
                        flash('Multiple choice questions need at least 2 options!', 'danger')
                        return redirect(url_for('add_challenge'))
                else:
                    # Handle normal text questions
                    options = []
                    solution = request.form['Solution']
                save_challenge(name, question, solution, kategory, options, points)
                flash('Question successfully added!', 'success')
                return redirect(url_for('add_challenge'))

        # Move database query inside the route function
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name, question, solution, kategory, points FROM questions')
        challenges = c.fetchall()
        conn.close()
        return render_template('add_challenge.html', challenges=challenges)
    
    @app.route('/add_hint', methods=['POST'])
    def add_hint():
        if 'role' in session and session['role'] == 'Admin':
            challenge_id = request.form.get('challenge_id')
            hint = request.form.get('hint')
            costs = request.form.get('costs')

            if challenge_id and hint and costs:
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('INSERT INTO help (challenge_id, hint, costs) VALUES (?, ?, ?)', (challenge_id, hint, costs))
                conn.commit()
                conn.close()
                flash('Hint successfully added!', 'success')
            else:
                flash('Please fill in all fields', 'error')

        return redirect(url_for('add_challenge'))
    
    @app.route('/buy_hint', methods=['POST'])
    def buy_hint():
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'})

        data = request.get_json()
        points_cost = data.get('points')
        challenge_id = data.get('challengeId')
        username = session['username']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        # Prüfe ob der Hint bereits gekauft wurde
        c.execute('SELECT id FROM purchased_hints WHERE username = ? AND challenge_id = ?', 
                 (username, challenge_id))
        if c.fetchone():
            conn.close()
            return jsonify({'success': True, 'alreadyPurchased': True})

        # Prüfe Punktestand
        c.execute('SELECT blackmarket_points FROM users WHERE username = ?', (username,))
        current_points = c.fetchone()[0]

        if current_points < int(points_cost):
            conn.close()
            return jsonify({'success': False, 'error': 'Not enough points'})

        # Ziehe Punkte ab und speichere den Kauf
        new_points = current_points - int(points_cost)
        c.execute('UPDATE users SET blackmarket_points = ? WHERE username = ?', (new_points, username))
        c.execute('INSERT INTO purchased_hints (username, challenge_id) VALUES (?, ?)', 
                 (username, challenge_id))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'newPoints': new_points,
            'alreadyPurchased': False
        })
    
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
    
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"}), 200