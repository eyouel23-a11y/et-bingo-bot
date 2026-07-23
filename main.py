import os
import random
import time
import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (telegram_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, balance REAL DEFAULT 0.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS game_history 
                 (game_id INTEGER PRIMARY KEY AUTOINCREMENT, winner_name TEXT, winning_number TEXT, pattern_type TEXT, prize_amount REAL DEFAULT 0.0, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    # Migrate: add missing columns to game_history if they don't exist yet
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(game_history)")}
    for col, typedef in [("pattern_type", "TEXT"), ("prize_amount", "REAL DEFAULT 0.0")]:
        if col not in existing_cols:
            c.execute(f"ALTER TABLE game_history ADD COLUMN {col} {typedef}")
    c.execute('''CREATE TABLE IF NOT EXISTS deposit_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  telegram_id INTEGER, name TEXT, phone TEXT,
                  amount REAL, note TEXT,
                  status TEXT DEFAULT "pending",
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

game_id_counter = 1001
joined_players = set() # ለተዘጋጀው ጨዋታ ክፍያ የፈጸሙ ተጫዋቾች ዝርዝር (TG ID)

game_state = {
    "game_id": game_id_counter,
    "status": "waiting",
    "called_numbers": [],
    "winner": None,
    "winning_number": None,
    "entry_fee": 20.0,
    "pattern": "any_line",
    "last_call_time": 0
}

ALL_NUMBERS = list(range(1, 76))

def get_bingo_letter(num):
    if 1 <= num <= 15: return f"B-{num}"
    elif 16 <= num <= 30: return f"I-{num}"
    elif 31 <= num <= 45: return f"N-{num}"
    elif 46 <= num <= 60: return f"G-{num}"
    elif 61 <= num <= 75: return f"O-{num}"
    return str(num)

def calculate_prize():
    total_collected = len(joined_players) * game_state["entry_fee"]
    prize = total_collected * 0.75 # 75% ለተጫዋቹ
    return round(total_collected, 2), round(prize, 2)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin/users')
def admin_users():
    return render_template('admin_users.html')

@app.route('/admin/history')
def admin_history():
    return render_template('admin_history.html')

@app.route('/api/check_user', methods=['POST'])
def check_user():
    data = request.json
    tg_id = data.get('telegram_id')

    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, name, phone, balance FROM users WHERE telegram_id = ?", (tg_id,))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({
            "registered": True, 
            "name": user[1], 
            "phone": user[2], 
            "balance": user[3],
            "entry_fee": game_state["entry_fee"],
            "has_joined": tg_id in joined_players
        })
    return jsonify({"registered": False, "entry_fee": game_state["entry_fee"]})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    tg_id = data.get('telegram_id')
    name = data.get('name')
    phone = data.get('phone')

    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (telegram_id, name, phone, balance) VALUES (?, ?, ?, 0.0)", (tg_id, name, phone))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "name": name, "balance": 0.0})
    except Exception:
        conn.close()
        return jsonify({"status": "error", "message": "ቀድመው ተመዝግበዋል!"}), 400

@app.route('/api/join_game', methods=['POST'])
def join_game():
    global joined_players
    data = request.json
    tg_id = data.get('telegram_id')

    if game_state["status"] != "waiting":
        return jsonify({"status": "error", "message": "ጨዋታው ተጀምሯል! እባክዎ ቀጣዩን ጨዋታ ይጠብቁ።"})

    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE telegram_id = ?", (tg_id,))
    user = c.fetchone()

    fee = game_state["entry_fee"]
    if not user or user[0] < fee:
        conn.close()
        return jsonify({"status": "error", "message": f"❌ በቂ ባላንስ የለዎትም! መደቡ {fee} ETB ነው።"})

    if tg_id in joined_players:
        conn.close()
        return jsonify({"status": "error", "message": "አስቀድመው ተመዝግበዋል!"})

    c.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (fee, tg_id))
    conn.commit()
    conn.close()

    joined_players.add(tg_id)
    return jsonify({"status": "success", "message": "በጨዋታው ተሳታፊ ሆነዋል!"})

@app.route('/api/admin/data', methods=['GET'])
def get_admin_data():
    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, name, phone, balance FROM users")
    users = c.fetchall()

    c.execute("SELECT game_id, winner_name, winning_number, pattern_type, timestamp FROM game_history ORDER BY game_id DESC LIMIT 20")
    history = c.fetchall()
    conn.close()

    total_pool, prize = calculate_prize()

    user_list = [{"telegram_id": u[0], "name": u[1], "phone": u[2], "balance": u[3]} for u in users]
    history_list = [{"game_id": h[0], "winner": h[1], "winning_number": h[2], "pattern": h[3], "time": h[4]} for h in history]

    return jsonify({
        "users": user_list, 
        "history": history_list,
        "game_state": game_state,
        "joined_count": len(joined_players),
        "total_pool": total_pool,
        "prize_amount": prize
    })

@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, name, phone, balance FROM users")
    users = c.fetchall()
    conn.close()

    user_list = [{"telegram_id": u[0], "name": u[1], "phone": u[2], "balance": u[3]} for u in users]
    return jsonify({"users": user_list})

@app.route('/api/admin/update_balance', methods=['POST'])
def update_balance():
    data = request.json
    tg_id = data.get('telegram_id')
    amount = float(data.get('amount', 0))

    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, tg_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# ── Deposit request (player submits) ──────────────────────────────────
@app.route('/api/request_deposit', methods=['POST'])
def request_deposit():
    data = request.json or {}
    tg_id  = data.get('telegram_id')
    amount = float(data.get('amount', 0))
    note   = data.get('note', '')

    if amount <= 0:
        return jsonify({"status": "error", "message": "ትክክለኛ የብር መጠን ያስገቡ!"}), 400

    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("SELECT name, phone FROM users WHERE telegram_id = ?", (tg_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({"status": "error", "message": "ተጠቃሚ አልተገኘም!"}), 404

    c.execute(
        "INSERT INTO deposit_requests (telegram_id, name, phone, amount, note) VALUES (?,?,?,?,?)",
        (tg_id, user[0], user[1], amount, note)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "ጥያቄዎ ለአድሚን ተልኳል! ሲፈቀድ ባላንስዎ ይጨመራል።"})

# ── Admin: list pending deposit requests ──────────────────────────────
@app.route('/api/admin/deposit_requests', methods=['GET'])
def admin_deposit_requests():
    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("""SELECT id, telegram_id, name, phone, amount, note, status, created_at
                 FROM deposit_requests ORDER BY created_at DESC""")
    rows = c.fetchall()
    conn.close()
    keys = ["id","telegram_id","name","phone","amount","note","status","created_at"]
    return jsonify({"requests": [dict(zip(keys, r)) for r in rows]})

# ── Admin: approve / reject deposit request ────────────────────────────
@app.route('/api/admin/handle_deposit', methods=['POST'])
def handle_deposit():
    data   = request.json or {}
    req_id = data.get('req_id')
    action = data.get('action')   # "approve" or "reject"

    conn = sqlite3.connect('bingo.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, amount, status FROM deposit_requests WHERE id=?", (req_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "ጥያቄው አልተገኘም!"}), 404
    if row[2] != 'pending':
        conn.close()
        return jsonify({"status": "error", "message": "ጥያቄው ቀደም ሲሉ ተወስኗል!"}), 400

    if action == 'approve':
        c.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (row[1], row[0]))
        c.execute("UPDATE deposit_requests SET status='approved' WHERE id=?", (req_id,))
        msg = "ተፈቅዷል! ባላንስ ተደምሯል።"
    else:
        c.execute("UPDATE deposit_requests SET status='rejected' WHERE id=?", (req_id,))
        msg = "ተቀባይነት አልተሰጠውም።"

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": msg})

@app.route('/api/game_status', methods=['GET'])
def get_game_status():
    global game_state
    if game_state["status"] == "running":
        current_time = time.time()
        if current_time - game_state["last_call_time"] >= 3:
            called_raw = [int(x.split('-')[1]) for x in game_state["called_numbers"]]
            remaining = [n for n in ALL_NUMBERS if n not in called_raw]
            if remaining:
                next_num = random.choice(remaining)
                formatted_num = get_bingo_letter(next_num)
                game_state["called_numbers"].append(formatted_num)
                game_state["last_call_time"] = current_time
            else:
                game_state["status"] = "ended"

    total_pool, prize = calculate_prize()

    res_data = dict(game_state)
    res_data["joined_players"] = list(joined_players)
    res_data["joined_count"] = len(joined_players)
    res_data["total_pool"] = total_pool
    res_data["prize_amount"] = prize
    return jsonify(res_data)

@app.route('/api/admin_control', methods=['POST'])
def admin_control():
    global game_state, game_id_counter, joined_players
    data = request.json
    action = data.get('action')

    if action == 'start':
        if game_state["status"] in ["waiting", "paused"]:
            fee = float(data.get('entry_fee', 20.0))
            pattern = data.get('pattern', 'any_line')
            game_state["entry_fee"] = fee
            game_state["pattern"] = pattern
            game_state["status"] = "running"
            game_state["last_call_time"] = time.time()

    elif action == 'pause':
        game_state["status"] = "paused"
    elif action == 'reset':
        game_id_counter += 1
        joined_players.clear()
        game_state = {
            "game_id": game_id_counter,
            "status": "waiting",
            "called_numbers": [],
            "winner": None,
            "winning_number": None,
            "entry_fee": float(data.get('entry_fee', 20.0)),
            "pattern": data.get('pattern', 'any_line'),
            "last_call_time": 0
        }

    return jsonify({"status": "success", "game_state": game_state})

def verify_bingo(board, marked_indices, called_numbers, pattern):
    called_set = set()
    for call in called_numbers:
        val = call.split('-')[1] if '-' in call else call
        called_set.add(val)

    for idx in marked_indices:
        val = str(board[idx])
        if val != "FREE" and val not in called_set:
            return False

    lines = []
    for r in range(5):
        lines.append([r*5 + c for c in range(5)])
    for c in range(5):
        lines.append([r*5 + c for r in range(5)])
    lines.append([0, 6, 12, 18, 24])
    lines.append([4, 8, 12, 16, 20])

    completed_lines = 0
    for line in lines:
        if all(idx in marked_indices for idx in line):
            completed_lines += 1

    if pattern == "any_line" and completed_lines >= 1:
        return True
    elif pattern == "two_lines" and completed_lines >= 2:
        return True
    elif pattern == "full_house" and len(marked_indices) == 25:
        return True

    return False

@app.route('/api/claim_bingo', methods=['POST'])
def claim_bingo():
    global game_state
    data = request.json
    player_name = data.get('player_name', 'Player')
    tg_id = data.get('telegram_id')
    board = data.get('board', [])
    marked_indices = data.get('marked_indices', [])

    if tg_id not in joined_players:
        return jsonify({"status": "invalid", "message": "❌ በጨዋታው አልተመዘገቡም!"})

    if game_state["status"] == "running" and len(game_state["called_numbers"]) > 0:
        is_valid = verify_bingo(board, marked_indices, game_state["called_numbers"], game_state["pattern"])

        if is_valid:
            last_num = game_state["called_numbers"][-1]
            total_pool, prize = calculate_prize()

            game_state["status"] = "ended"
            game_state["winner"] = player_name
            game_state["winning_number"] = last_num

            # አሸናፊውን አካውንት ላይ 75% ሽልማቱን በቀጥታ ይጨምራል!
            conn = sqlite3.connect('bingo.db')
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (prize, tg_id))
            c.execute("INSERT INTO game_history (game_id, winner_name, winning_number, pattern_type, prize_amount) VALUES (?, ?, ?, ?, ?)",
                      (game_state["game_id"], player_name, last_num, game_state["pattern"], prize))
            conn.commit()
            conn.close()

            return jsonify({"status": "valid", "winner": player_name, "winning_number": last_num, "prize": prize})
        else:
            return jsonify({"status": "invalid", "message": "❌ ቢንጎ አልሰራም! የተመረጡት መስመሮች አልተሟሉም።"})

    return jsonify({"status": "invalid", "message": "ጨዋታው አልተጀመረም!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
