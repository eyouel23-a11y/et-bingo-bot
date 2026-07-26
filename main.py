import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Upload folder configuration
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            balance REAL DEFAULT 50.0
        )
    ''')

    # Deposits table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            amount REAL,
            screenshot TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # Withdrawals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            amount REAL,
            phone TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if not user:
                cursor.execute('INSERT INTO users (username, balance) VALUES (?, ?)', (username, 50.0))
                conn.commit()
            conn.close()
            session['username'] = username
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'deposit':
            amount = float(request.form.get('amount', 0))
            file = request.files.get('screenshot')
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute('INSERT INTO deposits (username, amount, screenshot, status) VALUES (?, ?, ?, ?)',
                               (session['username'], amount, filename, 'Pending'))
                conn.commit()
        elif action == 'withdraw':
            amount = float(request.form.get('amount', 0))
            phone = request.form.get('phone')
            cursor.execute('SELECT balance FROM users WHERE username = ?', (session['username'],))
            row = cursor.fetchone()
            current_balance = row[0] if row else 0
            if current_balance >= amount:
                cursor.execute('INSERT INTO withdrawals (username, amount, phone, status) VALUES (?, ?, ?, ?)',
                               (session['username'], amount, phone, 'Pending'))
                conn.commit()

    cursor.execute('SELECT balance FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    balance = user[0] if user else 0.0

    cursor.execute('SELECT * FROM deposits WHERE username = ?', (session['username'],))
    deposits = cursor.fetchall()

    cursor.execute('SELECT * FROM withdrawals WHERE username = ?', (session['username'],))
    withdrawals = cursor.fetchall()

    conn.close()
    return render_template('account.html', balance=balance, deposits=deposits, withdrawals=withdrawals)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        req_type = request.form.get('type')
        req_id = request.form.get('id')
        action = request.form.get('action')

        if req_type == 'deposit':
            if action == 'approve':
                cursor.execute('SELECT username, amount FROM deposits WHERE id = ?', (req_id,))
                dep = cursor.fetchone()
                if dep:
                    username, amount = dep
                    cursor.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, username))
                    cursor.execute("UPDATE deposits SET status = 'Approved' WHERE id = ?", (req_id,))
                    conn.commit()
            elif action == 'reject':
                cursor.execute("UPDATE deposits SET status = 'Rejected' WHERE id = ?", (req_id,))
                conn.commit()

        elif req_type == 'withdraw':
            if action == 'approve':
                cursor.execute('SELECT username, amount FROM withdrawals WHERE id = ?', (req_id,))
                wit = cursor.fetchone()
                if wit:
                    username, amount = wit
                    # ዊዝድሮ ሲጸድቅ ከባላንሱ ላይ በትክክል እንዲቀነስ ተደረገ
                    cursor.execute('UPDATE users SET balance = balance - ? WHERE username = ?', (amount, username))
                    cursor.execute("UPDATE withdrawals SET status = 'Approved' WHERE id = ?", (req_id,))
                    conn.commit()
            elif action == 'reject':
                cursor.execute("UPDATE withdrawals SET status = 'Rejected' WHERE id = ?", (req_id,))
                conn.commit()

    cursor.execute('SELECT * FROM deposits')
    deposits = cursor.fetchall()

    cursor.execute('SELECT * FROM withdrawals')
    withdrawals = cursor.fetchall()

    conn.close()
    return render_template('admin.html', deposits=deposits, withdrawals=withdrawals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
