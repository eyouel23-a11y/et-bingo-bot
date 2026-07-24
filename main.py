import os
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# --- IN-MEMORY DATABASE ---
users = {}          
deposit_requests = [] 
game_history = []

rooms = {
    "room_test_1": {"id": "room_test_1", "name": "🧪 የፈተና ክፍል (1 ሰው)", "entry_fee": 20, "max_players": 1},
    "room_20_5": {"id": "room_20_5", "name": "ባለ 20 ብር (5 ሰው)", "entry_fee": 20, "max_players": 5}
}

@app.route('/')
def index():
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

# --- API ENDPOINTS ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    phone = data.get('phone')
    if not phone: return jsonify({"success": False})
    if phone not in users:
        users[phone] = {"phone": phone, "balance": 0.0}
    return jsonify({"success": True, "balance": users[phone]["balance"]})

@app.route('/api/get_user', methods=['GET'])
def get_user():
    phone = request.args.get('phone')
    if phone in users:
        return jsonify({"success": True, "balance": users[phone]["balance"]})
    return jsonify({"success": False})

@app.route('/api/deposit', methods=['POST'])
def deposit():
    data = request.json or {}
    phone = data.get('phone')
    amount = float(data.get('amount', 0))
    req_id = len(deposit_requests) + 1
    deposit_requests.append({"id": req_id, "phone": phone, "amount": amount, "status": "pending"})
    return jsonify({"success": True, "message": "ዲፖዚትዎ ተልኳል!"})

@app.route('/api/admin/data', methods=['GET'])
def admin_data():
    pending = [r for r in deposit_requests if r["status"] == "pending"]
    all_users = list(users.values())
    return jsonify({"requests": pending, "users": all_users, "history": game_history})

@app.route('/api/admin/approve', methods=['POST'])
def admin_approve():
    data = request.json or {}
    req_id = data.get('req_id')
    for r in deposit_requests:
        if r["id"] == req_id and r["status"] == "pending":
            r["status"] = "approved"
            if r["phone"] in users:
                users[r["phone"]]["balance"] += r["amount"]
            return jsonify({"success": True, "message": "ተጸድቋል!"})
    return jsonify({"success": False, "message": "አልተገኘም!"})

@app.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.json or {}
    phone = data.get('phone')
    room_id = data.get('room_id')
    user = users.get(phone)
    room = rooms.get(room_id)

    if not user or not room:
        return jsonify({"success": False, "message": "ተጠቃሚው ወይም ክፍሉ አልተገኘም!"})

    if user['balance'] < room['entry_fee']:
        return jsonify({"success": False, "message": f"በቂ ባላንስ የለዎትም! (የሚጠበቀው: {room['entry_fee']})"})

    user['balance'] -= room['entry_fee']
    return jsonify({"success": True, "message": "ክፍሉን ተቀላቅለዋል!", "balance": user['balance']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
