from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

# Database Setup
def init_db():
    conn = sqlite3.connect('bingo_game.db')
    c = conn.cursor()
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    telegram_id TEXT PRIMARY KEY,
                    username TEXT,
                    phone TEXT,
                    balance REAL DEFAULT 0.0,
                    is_registered INTEGER DEFAULT 0
                )''')
    # Admin Wallet Table
    c.execute('''CREATE TABLE IF NOT EXISTS admin_wallet (
                    id INTEGER PRIMARY KEY,
                    total_earnings REAL DEFAULT 0.0
                )''')
    c.execute('''INSERT OR IGNORE INTO admin_wallet (id, total_earnings) VALUES (1, 0.0)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# Check User Status & Balance
@app.route('/api/check_user', methods=['POST'])
def check_user():
    data = request.json or {}
    tg_id = str(data.get('telegram_id', ''))
    username = data.get('username', 'NoUsername')

    conn = sqlite3.connect('bingo_game.db')
    c = conn.cursor()
    c.execute("SELECT phone, balance, is_registered FROM users WHERE telegram_id = ?", (tg_id,))
    user = c.fetchone()

    if user and user[2] == 1:
        conn.close()
        return jsonify({"registered": True, "phone": user[0], "balance": user[1]})
    else:
        c.execute("INSERT OR IGNORE INTO users (telegram_id, username, is_registered) VALUES (?, ?, 0)", (tg_id, username))
        conn.commit()
        conn.close()
        return jsonify({"registered": False, "balance": 0.0})

# Register Phone Number
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    tg_id = str(data.get('telegram_id', ''))
    phone = data.get('phone', '')

    conn = sqlite3.connect('bingo_game.db')
    c = conn.cursor()
    c.execute("UPDATE users SET phone = ?, is_registered = 1 WHERE telegram_id = ?", (phone, tg_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "ምዝገባው ተሳክቷል!"})

# ADMIN: Get All Users & Total Admin Cut
@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    conn = sqlite3.connect('bingo_game.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, username, phone, balance FROM users WHERE is_registered = 1")
    users = c.fetchall()
    c.execute("SELECT total_earnings FROM admin_wallet WHERE id = 1")
    admin_row = c.fetchone()
    admin_cut = admin_row[0] if admin_row else 0.0
    conn.close()
    return jsonify({"users": users, "admin_earnings": admin_cut})

# ADMIN: Deposit Money
@app.route('/api/admin/deposit', methods=['POST'])
def deposit():
    data = request.json or {}
    tg_id = str(data.get('telegram_id', ''))
    amount = float(data.get('amount', 0))

    conn = sqlite3.connect('bingo_game.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, tg_id))
    conn.commit()

    c.execute("SELECT balance FROM users WHERE telegram_id = ?", (tg_id,))
    new_bal = c.fetchone()[0]
    conn.close()
    return jsonify({"status": "success", "new_balance": new_bal})

# GAME: Deduct Bet Amount (25% to Admin, 75% to Prize Pool)
@app.route('/api/game/start_round', methods=['POST'])
def start_round():
    data = request.json or {}
    tg_id = str(data.get('telegram_id', ''))
    bet_amount = float(data.get('bet_amount', 30))

    conn = sqlite3.connect('bingo_game.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE telegram_id = ?", (tg_id,))
    row = c.fetchone()

    if not row or row[0] < bet_amount:
        conn.close()
        return jsonify({"status": "error", "message": "Incalculable/Insufficient balance!"}), 400

    # Deduct balance
    c.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (bet_amount, tg_id))
    admin_cut = bet_amount * 0.25
    c.execute("UPDATE admin_wallet SET total_earnings = total_earnings + ? WHERE id = 1", (admin_cut,))

    conn.commit()
    c.execute("SELECT balance FROM users WHERE telegram_id = ?", (tg_id,))
    rem_balance = c.fetchone()[0]
    conn.close()

    return jsonify({"status": "success", "remaining_balance": rem_balance})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
