import os
from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Upload Folder Configuration for Telebirr Screenshots
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- IN-MEMORY DATABASE ---
users = {}            # phone -> {phone, name, balance}
deposit_requests = [] # [{id, phone, name, amount, proof, status}]
withdrawal_requests = [] # [{id, phone, name, amount, status}]
game_history = []     # [{game_id, room_name, winner_name, winner_phone, total_pool, prize, house_cut}]

# 12 Rooms Structure (3 Price Tiers x 4 Capacities)
rooms = {}
prices = [20, 40, 100]
capacities = [5, 8, 10, 15]

for price in prices:
    for cap in capacities:
        room_id = f"room_{price}_{cap}"
        rooms[room_id] = {
            "id": room_id,
            "name": f"ባለ {price} ብር ({cap} ሰው)",
            "entry_fee": price,
            "max_players": cap,
            "players": [],
            "status": "waiting"
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/account')
def account():
    return render_template('account.html')

@app.route('/rooms')
def rooms_page():
    return render_template('rooms.html')

@app.route('/game')
def game_page():
    return render_template('game.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# --- API ENDPOINTS ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    name = data.get('name')
    phone = data.get('phone')
    if not phone or not name:
        return jsonify({"success": False, "message": "ስም እና ስልክ ቁጥር ያስገቡ!"})

    if phone not in users:
        users[phone] = {"phone": phone, "name": name, "balance": 0.0}
    else:
        users[phone]["name"] = name

    return jsonify({"success": True, "balance": users[phone]["balance"]})

@app.route('/api/get_user', methods=['GET'])
def get_user():
    phone = request.args.get('phone')
    if phone in users:
        return jsonify({"success": True, "user": users[phone]})
    return jsonify({"success": False})

@app.route('/api/deposit', methods=['POST'])
def deposit():
    phone = request.form.get('phone')
    amount = float(request.form.get('amount', 0))

    if phone not in users:
        return jsonify({"success": False, "message": "ተጠቃሚው አልተገኘም!"})

    proof_filename = "default.jpg"
    if 'proof' in request.files:
        file = request.files['proof']
        if file.filename != '':
            filename = secure_filename(file.filename)
            # Make unique filename using phone and length
            proof_filename = f"{phone}_{len(deposit_requests)}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], proof_filename))

    req_id = len(deposit_requests) + 1
    deposit_requests.append({
        "id": req_id,
        "phone": phone,
        "name": users[phone]["name"],
        "amount": amount,
        "proof": proof_filename,
        "status": "pending"
    })
    return jsonify({"success": True, "message": "የዲፖዚት ጥያቄዎ እና ስክሪንሾቱ በአግባቡ ተልኳል! አድሚን ሲያረጋግጠው አካውንትዎ ላይ ይገባል።"})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json or {}
    phone = data.get('phone')
    amount = float(data.get('amount', 0))

    if phone not in users:
        return jsonify({"success": False, "message": "ተጠቃሚው አልተገኘም!"})

    user = users[phone]
    if amount <= 0 or amount > user["balance"]:
        return jsonify({"success": False, "message": "ያስገቡት የገንዘብ መጠን ከባላንሶ በላይ ነው ወይም ትክክለኛ አይደለም!"})

    req_id = len(withdrawal_requests) + 1
    withdrawal_requests.append({
        "id": req_id,
        "phone": phone,
        "name": user["name"],
        "amount": amount,
        "status": "pending"
    })
    return jsonify({"success": True, "message": "የዊዝድሮዋል ጥያቄዎ ተልኳል!"})

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    room_list = []
    for r_id, r_data in rooms.items():
        room_list.append({
            "id": r_data["id"],
            "name": r_data["name"],
            "entry_fee": r_data["entry_fee"],
            "max_players": r_data["max_players"],
            "current_players": len(r_data["players"]),
            "status": r_data["status"]
        })
    return jsonify({"success": True, "rooms": room_list})

@app.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.json or {}
    phone = data.get('phone')
    room_id = data.get('room_id')

    user = users.get(phone)
    room = rooms.get(room_id)

    if not user or not room:
        return jsonify({"success": False, "message": "ተጠቃሚው ወይም ክፍሉ አልተገኘም!"})

    if room["status"] != "waiting":
        return jsonify({"success": False, "message": "ጨዋታው უკვე ጀምሯል ወይም አልቋል!"})

    if any(p["phone"] == phone for p in room["players"]):
        return jsonify({"success": True, "room": room})

    if user["balance"] < room["entry_fee"]:
        return jsonify({"success": False, "message": f"በቂ ባላንስ የለዎትም! (የሚጠበቀው: {room['entry_fee']} ብር)"})

    user["balance"] -= room["entry_fee"]
    room["players"].append({"phone": phone, "name": user["name"]})

    if len(room["players"]) >= room["max_players"]:
        room["status"] = "started"

    return jsonify({"success": True, "balance": user["balance"], "room": room})

@app.route('/api/room_status', methods=['GET'])
def room_status():
    room_id = request.args.get('room_id')
    room = rooms.get(room_id)
    if not room:
        return jsonify({"success": False})
    return jsonify({
        "success": True,
        "current_players": len(room["players"]),
        "max_players": room["max_players"],
        "status": room["status"],
        "players": room["players"]
    })

@app.route('/api/claim_win', methods=['POST'])
def claim_win():
    data = request.json or {}
    phone = data.get('phone')
    room_id = data.get('room_id')

    user = users.get(phone)
    room = rooms.get(room_id)

    if not user or not room:
        return jsonify({"success": False, "message": "ስህተት ተፈጥሯል!"})

    total_pool = room["entry_fee"] * len(room["players"])
    prize = total_pool * 0.75
    house_cut = total_pool * 0.25

    user["balance"] += prize

    game_id = f"GM-{len(game_history) + 101}"
    game_history.append({
        "game_id": game_id,
        "room_name": room["name"],
        "winner_name": user["name"],
        "winner_phone": phone,
        "total_pool": total_pool,
        "prize": prize,
        "house_cut": house_cut
    })

    room["players"] = []
    room["status"] = "waiting"

    return jsonify({"success": True, "prize": prize, "balance": user["balance"], "message": f"እንኳን ደስ አለዎት! {prize} ብር አሸንፈዋል!"})

# --- ADMIN API ENDPOINTS ---
@app.route('/api/admin/data', methods=['GET'])
def admin_data():
    return jsonify({
        "users": list(users.values()),
        "deposits": deposit_requests,
        "withdrawals": withdrawal_requests,
        "history": game_history
    })

@app.route('/api/admin/approve_deposit', methods=['POST'])
def approve_deposit():
    data = request.json or {}
    req_id = data.get('req_id')
    for req in deposit_requests:
        if req["id"] == req_id and req["status"] == "pending":
            req["status"] = "approved"
            phone = req["phone"]
            if phone in users:
                users[phone]["balance"] += req["amount"]
            return jsonify({"success": True, "message": "ዲፖዚቱ ተጸድቆ አካውንት ላይ ገብቷል!"})
    return jsonify({"success": False, "message": "ጥያቄው አልተገኘም!"})

@app.route('/api/admin/approve_withdraw', methods=['POST'])
def approve_withdraw():
    data = request.json or {}
    req_id = data.get('req_id')
    for req in withdrawal_requests:
        if req["id"] == req_id and req["status"] == "pending":
            req["status"] = "approved"
            return jsonify({"success": True, "message": "ዊዝድሮዋል ጥያቄው ተጸድቋል!"})
    return jsonify({"success": False, "message": "ጥያቄው አልተገኘም!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
