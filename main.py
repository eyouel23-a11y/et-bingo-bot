import os
import random
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# --- IN-MEMORY DATABASE ---
users = {
    "user_1": {"name": "Player 1", "balance": 100.0, "telebirr": "0911000000"},
    "user_2": {"name": "Player 2", "balance": 50.0, "telebirr": "0922000000"}
}

# በ Button መልክ የሚመጡት የጨዋታ ክፍሎች (Rooms)
rooms = {
    "room_20_5": {"id": "room_20_5", "name": "ባለ 20 ብር (5 ሰው)", "entry_fee": 20, "max_players": 5, "players": [], "status": "waiting", "drawn_numbers": []},
    "room_30_5": {"id": "room_30_5", "name": "ባለ 30 ብር (5 ሰው)", "entry_fee": 30, "max_players": 5, "players": [], "status": "waiting", "drawn_numbers": []},
    "room_40_5": {"id": "room_40_5", "name": "ባለ 40 ብር (5 ሰው)", "entry_fee": 40, "max_players": 5, "players": [], "status": "waiting", "drawn_numbers": []},
    "room_30_10": {"id": "room_30_10", "name": "ባለ 30 ብር (10 ሰው)", "entry_fee": 30, "max_players": 10, "players": [], "status": "waiting", "drawn_numbers": []}
}

deposit_requests = []
withdrawal_requests = []

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# 1. ለተጠቃሚው የአማራጭ ክፍሎችን (Buttons) መላክ
@app.route('/api/get_rooms', methods=['GET'])
def get_rooms():
    room_list = []
    for r in rooms.values():
        room_list.append({
            "id": r["id"],
            "name": r["name"],
            "entry_fee": r["entry_fee"],
            "max_players": r["max_players"],
            "current_players": len(r["players"]),
            "status": r["status"]
        })
    return jsonify({"success": True, "rooms": room_list})

# 2. ወደ ክፍል መቀላቀል (ገንዘብ አይቆረጥም!)
@app.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.json
    user_id = data.get('user_id')
    room_id = data.get('room_id')

    user = users.get(user_id)
    room = rooms.get(room_id)

    if not user or not room:
        return jsonify({"success": False, "message": "መረጃው አልተገኘም!"}), 404

    # ተጫዋቹ በቂ ባላንስ እንዳለው ማረጋገጥ ብቻ (አይቆረጥም)
    if user['balance'] < room['entry_fee']:
        return jsonify({"success": False, "message": "ለዚህ ክፍል በቂ ባላንስ የለህም!"}), 400

    if user_id in room['players']:
        return jsonify({"success": False, "message": "ቀድመህ ገብተሃል!"}), 400

    # ተጫዋቹን ክፍል ውስጥ ማካተት
    room['players'].append(user_id)

    # 🚀 ቁጥሩ ሲሞላ ብቻ AUTO-START እና ብር መቁረጥ!
    if len(room['players']) == room['max_players']:
        room['status'] = "playing"

        # የሁሉም ተጫዋቾች ብር አሁን ይቆረጣል
        for pid in room['players']:
            users[pid]['balance'] -= room['entry_fee']

        # ጨዋታውን መጀመር (ቁጥሮችን ማውጣት)
        room['drawn_numbers'] = random.sample(range(1, 76), 75)

    return jsonify({
        "success": True, 
        "message": "በስኬት ተቀላቅለሃል!",
        "current_players": len(room['players']),
        "max_players": room['max_players'],
        "status": room['status']
    })

# 3. 75% የአሸናፊነት ባላንስ አደማመር (Auto Winner)
@app.route('/api/claim_bingo', methods=['POST'])
def claim_bingo():
    data = request.json
    user_id = data.get('user_id')
    room_id = data.get('room_id')

    room = rooms.get(room_id)
    user = users.get(user_id)

    if not room or room['status'] != "playing":
        return jsonify({"success": False, "message": "ጨዋታው አልተጀመረም!"}), 400

    # 75% የሽልማት ስሌት
    total_pool = room['entry_fee'] * room['max_players']
    winner_prize = total_pool * 0.75

    # አውቶማቲክ ባላንስ መደመር
    user['balance'] += winner_prize
    room['status'] = "finished"

    return jsonify({
        "success": True,
        "message": f"እንኳን ደስ አለህ! BINGO ብለሃል። {winner_prize} ብር ባላንስህ ላይ ተደምሯል!",
        "new_balance": user['balance']
    })

# 4. TELEBIRR DEPOSIT & WITHDRAWAL
@app.route('/api/deposit', methods=['POST'])
def deposit():
    data = request.json
    deposit_requests.append({
        "user_id": data.get('user_id'),
        "amount": float(data.get('amount')),
        "tx_id": data.get('tx_id'),
        "status": "pending"
    })
    return jsonify({"success": True, "message": "የገቢ ጥያቄህ ለአድሚን ተልኳል!"})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user_id = data.get('user_id')
    amount = float(data.get('amount'))
    user = users.get(user_id)

    if user['balance'] < amount:
        return jsonify({"success": False, "message": "በቂ ባላንስ የለህም!"}), 400

    user['balance'] -= amount
    withdrawal_requests.append({
        "user_id": user_id,
        "amount": amount,
        "telebirr": data.get('telebirr'),
        "status": "pending"
    })
    return jsonify({"success": True, "message": "የወጪ ጥያቄህ ተልኳል!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
