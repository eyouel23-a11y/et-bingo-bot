import os
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# --- IN-MEMORY DATABASE ---
users = {}          
deposit_requests = [] 

rooms = {
    "room_test_1": {"id": "room_test_1", "name": "🧪 የፈተና ክፍል (1 ሰው)", "entry_fee": 20, "max_players": 1, "players": [], "status": "waiting"},
    "room_20_5": {"id": "room_20_5", "name": "ባለ 20 ብር (5 ሰው)", "entry_fee": 20, "max_players": 5, "players": [], "status": "waiting"},
    "room_30_5": {"id": "room_30_5", "name": "ባለ 30 ብር (5 ሰው)", "entry_fee": 30, "max_players": 5, "players": [], "status": "waiting"}
}

# --- HTML & FRONTEND (USER APP) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ET Bingo Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: sans-serif; background: #121212; color: #fff; margin: 0; padding: 12px; text-align: center; }
        .card { background: #1e1e1e; padding: 15px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .btn { background: #2481cc; color: white; border: none; padding: 10px; font-size: 14px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; margin-top: 5px; }
        .btn-success { background: #4CAF50; }
        input { width: 90%; padding: 10px; margin: 6px 0; border-radius: 6px; border: 1px solid #444; background: #121212; color: white; }
        .bingo-board { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; max-width: 350px; margin: 15px auto; background: #2a2a2a; padding: 8px; border-radius: 10px; }
        .bingo-cell { background: #1e1e1e; border: 1px solid #444; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; border-radius: 6px; cursor: pointer; }
        .bingo-cell.marked { background: #4CAF50; color: white; }
    </style>
</head>
<body>

    <div id="reg-screen" class="card">
        <h2>👋 እንኳን ወደ ET Bingo መጡ</h2>
        <p>ለመጀመር ስልክ ቁጥርዎን ያስገቡ</p>
        <input type="text" id="reg-phone" placeholder="ስልክ ቁጥር (ምሳሌ: 0911...)">
        <button class="btn btn-success" onclick="registerUser()">ይመዝገቡ</button>
    </div>

    <div id="main-screen" class="card" style="display:none;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span><b>🎲 ET BINGO</b></span>
            <span style="color:#ff9800; font-weight:bold;">💰 <span id="balance">0.00</span> ETB</span>
        </div>
        <hr style="border-color:#333; margin:10px 0;">
        <h3>የጨዋታ ክፍሎች</h3>
        <button class="btn btn-success" onclick="joinRoom('room_test_1')">🧪 የፈተና ክፍል (20 ብር)</button>
        <button class="btn" onclick="joinRoom('room_20_5')">ባለ 20 ብር (5 ሰው)</button>

        <div id="game-area" style="display:none; margin-top:15px;">
            <h4>የቢንጎ ካርድዎ</h4>
            <div class="bingo-board" id="board"></div>
            <button class="btn" style="background:#ff9800; color:black;" onclick="claimBingo()">🎉 BINGO አውራ!</button>
        </div>

        <hr style="border-color:#333; margin:15px 0;">
        <h3>📲 ቴሌብር ዲፖዚት</h3>
        <p style="font-size:12px; color:#aaa;">ሂሳብ ለመጫን ወደ <b>0982289449</b> ያስተላልፉ</p>
        <input type="number" id="dep-amount" placeholder="የብር መጠን">
        <button class="btn btn-success" onclick="sendDeposit()">ዲፖዚት ላክ</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        let userPhone = localStorage.getItem('bingo_phone') || '';
        if(userPhone) {
            checkUser(userPhone);
        }

        function registerUser() {
            const phone = document.getElementById('reg-phone').value.trim();
            if(!phone) return alert('ስልክ ቁጥር ያስገቡ!');

            fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone: phone})
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    localStorage.setItem('bingo_phone', phone);
                    userPhone = phone;
                    document.getElementById('reg-screen').style.display = 'none';
                    document.getElementById('main-screen').style.display = 'block';
                    document.getElementById('balance').innerText = data.balance;
                }
            });
        }

        function checkUser(phone) {
            fetch('/api/get_user?phone=' + encodeURIComponent(phone))
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    document.getElementById('reg-screen').style.display = 'none';
                    document.getElementById('main-screen').style.display = 'block';
                    document.getElementById('balance').innerText = data.balance;
                }
            });
        }

        function sendDeposit() {
            const amount = document.getElementById('dep-amount').value;
            if(!amount) return alert('ብር ያስገቡ!');
            fetch('/api/deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone: userPhone, amount: amount})
            }).then(res => res.json()).then(data => alert(data.message));
        }

        function joinRoom(roomId) {
            fetch('/api/join_room', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone: userPhone, room_id: roomId})
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                if(data.success) {
                    document.getElementById('balance').innerText = data.balance;
                    document.getElementById('game-area').style.display = 'block';
                    buildBoard();
                }
            });
        }

        function buildBoard() {
            const board = document.getElementById('board');
            board.innerHTML = '';
            for(let i=1; i<=25; i++) {
                const cell = document.createElement('div');
                cell.className = 'bingo-cell';
                cell.innerText = i === 13 ? 'FREE' : Math.floor(Math.random() * 70) + 1;
                if(i === 13) cell.classList.add('marked');
                cell.onclick = () => cell.classList.toggle('marked');
                board.appendChild(cell);
            }
        }

        function claimBingo() {
            alert('🎉 እንኳን ደስ አለዎት! ሎተሪውን አሸንፈዋል!');
            location.reload();
        }
    </script>
</body>
</html>
"""

# --- ADMIN PANEL TEMPLATE ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <title>Admin Panel</title>
    <style>
        body { font-family: sans-serif; background: #111; color: #fff; padding: 20px; }
        .card { background: #1a1a1a; padding: 15px; border-radius: 10px; margin-bottom: 15px; }
        .btn { background: #4CAF50; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <h2>🛠️ Admin Dashboard</h2>
    <div class="card">
        <h3>📥 የዲፖዚት ጥያቄዎች</h3>
        <div id="reqs">መረጃ በመጫን ላይ...</div>
    </div>
    <div class="card">
        <h3>👥 ተጠቃሚዎች</h3>
        <div id="users">መረጃ በመጫን ላይ...</div>
    </div>

    <script>
        function loadData() {
            fetch('/api/admin/data')
            .then(res => res.json())
            .then(data => {
                const reqDiv = document.getElementById('reqs');
                if(data.requests.length === 0) {
                    reqDiv.innerHTML = 'ምንም ጥያቄ የለም።';
                } else {
                    reqDiv.innerHTML = '';
                    data.requests.forEach(r => {
                        reqDiv.innerHTML += `<p>${r.phone} - ${r.amount} ETB <button class="btn" onclick="approve(${r.id})">አረጋግጥ</button></p>`;
                    });
                }

                const userDiv = document.getElementById('users');
                if(data.users.length === 0) {
                    userDiv.innerHTML = 'ምንም ተጠቃሚ የለም።';
                } else {
                    userDiv.innerHTML = '';
                    data.users.forEach(u => {
                        userDiv.innerHTML += `<p>${u.phone} - <b>${u.balance} ETB</b></p>`;
                    });
                }
            });
        }

        function approve(id) {
            fetch('/api/admin/approve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({req_id: id})
            }).then(res => res.json()).then(data => { alert(data.message); loadData(); });
        }

        loadData();
    </script>
</body>
</html>
"""

# --- API ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/admin')
def admin():
    return render_template_string(ADMIN_TEMPLATE)

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
    return jsonify({"requests": pending, "users": all_users})

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
