import os
import random
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# --- IN-MEMORY DATABASE ---
users = {}          
deposit_requests = [] 

admin_telebirr = "0982289449"

rooms = {
    "room_test_1": {"id": "room_test_1", "name": "🧪 የፈተና ክፍል (ለፍተሻ 20 ብር - 1 ሰው)", "entry_fee": 20, "max_players": 1, "players": [], "status": "waiting"},
    "room_20_5": {"id": "room_20_5", "name": "ባለ 20 ብር (5 ሰው)", "entry_fee": 20, "max_players": 5, "players": [], "status": "waiting"},
    "room_30_5": {"id": "room_30_5", "name": "ባለ 30 ብር (5 ሰው)", "entry_fee": 30, "max_players": 5, "players": [], "status": "waiting"},
    "room_40_5": {"id": "room_40_5", "name": "ባለ 40 ብር (5 ሰው)", "entry_fee": 40, "max_players": 5, "players": [], "status": "waiting"},
    "room_30_10": {"id": "room_30_10", "name": "ባለ 30 ብር (10 ሰው)", "entry_fee": 30, "max_players": 10, "players": [], "status": "waiting"}
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
        :root {
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --accent-color: #ff9800;
            --text-color: #ffffff;
            --btn-blue: #2481cc;
            --btn-green: #4CAF50;
            --btn-red: #f44336;
        }
        body { font-family: sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 12px; text-align: center; }
        .card { background: var(--card-bg); padding: 15px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .balance-box { font-size: 18px; font-weight: bold; color: var(--accent-color); }
        .section-title { font-size: 16px; margin: 15px 0 10px 0; text-align: left; border-left: 4px solid var(--accent-color); padding-left: 8px; }
        .rooms-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .room-card { background: var(--card-bg); border: 1px solid #333; border-radius: 10px; padding: 12px; text-align: center; }
        .room-card h4 { margin: 0 0 5px 0; color: #fff; font-size: 14px; }
        .room-card p { margin: 0 0 8px 0; font-size: 12px; color: #aaa; }
        .btn { background-color: var(--btn-blue); color: white; border: none; padding: 10px; font-size: 14px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        .btn-success { background-color: var(--btn-green); }
        .btn-danger { background-color: var(--btn-red); }
        .btn-bingo { background-color: var(--accent-color); font-size: 20px; padding: 15px; margin-top: 15px; }
        input { width: 90%; padding: 10px; margin: 6px 0; border-radius: 6px; border: 1px solid #444; background: #121212; color: white; }
        .bingo-board { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; max-width: 350px; margin: 15px auto; background: #2a2a2a; padding: 8px; border-radius: 10px; }
        .bingo-cell { background: #1e1e1e; border: 1px solid #444; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; border-radius: 6px; cursor: pointer; }
        .bingo-cell.marked { background-color: var(--btn-green); color: white; }
        .bingo-cell.free { background-color: var(--accent-color); color: black; font-size: 12px; }
    </style>
</head>
<body>

    <!-- Registration Screen -->
    <div id="reg-screen" class="card">
        <h2>👋 እንኳን ወደ ET Bingo መጡ</h2>
        <p>ለመጀመር ስልክ ቁጥርዎን ያስገቡ</p>
        <input type="text" id="reg-phone" placeholder="ስልክ ቁጥር (ምሳሌ: 0911...)">
        <button class="btn btn-success" onclick="registerUser()">ይመዝገቡ (Register)</button>
    </div>

    <!-- Main App Screen -->
    <div id="main-screen" style="display:none;">
        <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
            <div><b>🎲 ET BINGO</b></div>
            <div class="balance-box">💰 <span id="balance">0.00</span> ETB</div>
        </div>

        <!-- Active Game Section -->
        <div id="game-section" class="card" style="display:none;">
            <div style="background:#222; padding:10px; border-radius:8px; font-size:18px; margin-bottom:10px;">
                የወጣው ቁጥር፦ <span id="current-drawn-num" style="color:var(--accent-color); font-weight:bold;">-</span>
            </div>
            <div class="bingo-board" id="bingo-board"></div>
            <button class="btn btn-bingo" onclick="claimBingo()">🎉 BINGO!</button>
        </div>

        <!-- Rooms Section -->
        <div id="rooms-section" class="card">
            <div class="section-title">የጨዋታ ክፍሎች (Auto Rooms)</div>
            <div class="rooms-grid" style="grid-template-columns: 1fr;">
                <div class="room-card" style="border: 2px solid var(--accent-color);">
                    <h4 style="color:var(--accent-color);">🧪 የፈተና ክፍል (1 ሰው ብቻ)</h4>
                    <p>የመግቢያ ዋጋ፦ 20 ብር</p>
                    <button class="btn btn-success" onclick="joinRoom('room_test_1')">በፍጥነት ሞክር (Test Join)</button>
                </div>
            </div>
            <div class="rooms-grid" style="margin-top: 10px;">
                <div class="room-card">
                    <h4>ባለ 20 ብር</h4>
                    <p>5 ተጫዋቾች</p>
                    <button class="btn" onclick="joinRoom('room_20_5')">ተቀላቀል</button>
                </div>
                <div class="room-card">
                    <h4>ባለ 30 ብር</h4>
                    <p>5 ተጫዋቾች</p>
                    <button class="btn" onclick="joinRoom('room_30_5')">ተቀላቀል</button>
                </div>
                <div class="room-card">
                    <h4>ባለ 40 ብር</h4>
                    <p>5 ተጫዋቾች</p>
                    <button class="btn" onclick="joinRoom('room_40_5')">ተቀላቀል</button>
                </div>
                <div class="room-card">
                    <h4>ባለ 30 ብር</h4>
                    <p>10 ተጫዋቾች</p>
                    <button class="btn" onclick="joinRoom('room_30_10')">ተቀላቀል</button>
                </div>
            </div>
        </div>

        <!-- Telebirr Deposit Section -->
        <div class="card">
            <div class="section-title" style="margin-top:0;">📲 ቴሌብር ሂሳብ ማስገባት (Deposit)</div>
            <p style="font-size: 13px; color: #aaa; text-align: left;">በዚህ የቴሌብር ቁጥር ብር ያስተላልፉ፦ <b style="color:var(--accent-color);">0982289449</b></p>
            <input type="number" id="dep-amount" placeholder="የአስገቡት የብር መጠን">
            <input type="file" id="dep-file" accept="image/*" style="background:none; border:none; color:white;">
            <button class="btn btn-success" onclick="sendDepositRequest()">የክፍያ ማረጋገጫ ላክ</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        let currentUserPhone = localStorage.getItem('bingo_user_phone');
        let currentRoomId = null;

        if (currentUserPhone) {
            checkUserSession(currentUserPhone);
        }

        function registerUser() {
            const phone = document.getElementById('reg-phone').value;
            if(!phone) return alert('እባክዎን ስልክ ቁጥር ያስገቡ!');

            fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: phone })
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    localStorage.setItem('bingo_user_phone', phone);
                    currentUserPhone = phone;
                    document.getElementById('reg-screen').style.display = 'none';
                    document.getElementById('main-screen').style.display = 'block';
                    document.getElementById('balance').innerText = data.balance;
                } else {
                    alert(data.message);
                }
            });
        }

        function checkUserSession(phone) {
            fetch('/api/get_user?phone=' + phone)
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    document.getElementById('reg-screen').style.display = 'none';
                    document.getElementById('main-screen').style.display = 'block';
                    document.getElementById('balance').innerText = data.balance;
                }
            });
        }

        function sendDepositRequest() {
            const amount = document.getElementById('dep-amount').value;
            const fileInput = document.getElementById('dep-file');
            if(!amount) return alert('እባክዎን የብር መጠኑን ያስገቡ!');

            let reader = new FileReader();
            if(fileInput.files[0]) {
                reader.readAsDataURL(fileInput.files[0]);
                reader.onload = function () {
                    postDeposit(amount, reader.result);
                };
            } else {
                postDeposit(amount, "");
            }
        }

        function postDeposit(amount, imgData) {
            fetch('/api/deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: currentUserPhone, amount: amount, screenshot: imgData })
            })
            .then(res => res.json())
            .then(data => alert(data.message));
        }

        function generateBingoCard() {
            const board = document.getElementById('bingo-board');
            board.innerHTML = '';
            let nums = [];
            while(nums.length < 24) {
                let r = Math.floor(Math.random() * 75) + 1;
                if(!nums.includes(r)) nums.push(r);
            }
            let cellCount = 0;
            for(let i=0; i<25; i++) {
                const cell = document.createElement('div');
                cell.classList.add('bingo-cell');
                if(i === 12) {
                    cell.innerText = 'FREE';
                    cell.classList.add('free', 'marked');
                } else {
                    cell.innerText = nums[cellCount];
                    cellCount++;
                    cell.onclick = function() { cell.classList.toggle('marked'); };
                }
                board.appendChild(cell);
            }
        }

        function joinRoom(roomId) {
            currentRoomId = roomId;
            fetch('/api/join_room', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: currentUserPhone, room_id: roomId })
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                if(data.success) {
                    document.getElementById('balance').innerText = data.balance;
                    document.getElementById('rooms-section').style.display = 'none';
                    document.getElementById('game-section').style.display = 'block';
                    generateBingoCard();
                }
            });
        }

        function claimBingo() {
            if(!currentRoomId) return;
            fetch('/api/claim_bingo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: currentUserPhone, room_id: currentRoomId })
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                if(data.success) {
                    document.getElementById('balance').innerText = data.new_balance;
                    document.getElementById('game-section').style.display = 'none';
                    document.getElementById('rooms-section').style.display = 'block';
                }
            });
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
    <title>Admin Dashboard</title>
    <style>
        body { font-family: sans-serif; background: #111; color: #fff; padding: 20px; }
        .section { background: #1a1a1a; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .req-card { background: #222; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #ff9800; }
        .user-row { background: #222; padding: 10px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .btn { background: #4CAF50; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        img { max-width: 200px; border-radius: 5px; margin-top: 10px; display: block; }
    </style>
</head>
<body>
    <h2>🛠️ Admin Dashboard</h2>

    <div class="section">
        <h3>📥 የዲፖዚት ጥያቄዎች (Deposit Requests)</h3>
        <div id="requests-container">ምንም አዲስ የዲፖዚት ጥያቄ የለም።</div>
    </div>

    <div class="section">
        <h3>👥 የተመዝጋቢዎች ዝርዝር (All Registered Users)</h3>
        <div id="users-container">ምንም ተመዝጋቢ የለም።</div>
    </div>

    <script>
        function loadAdminData() {
            fetch('/api/admin/requests')
            .then(res => res.json())
            .then(data => {
                const container = document.getElementById('requests-container');
                if(data.requests.length === 0) {
                    container.innerHTML = 'ምንም አዲስ የዲፖዚት ጥያቄ የለም።';
                } else {
                    container.innerHTML = '';
                    data.requests.forEach(req => {
                        container.innerHTML += `
                            <div class="req-card">
                                <p><b>ስልክ ቁጥር፦</b> ${req.phone}</p>
                                <p><b>የጠየቀው ብር፦</b> ${req.amount} ETB</p>
                                ${req.screenshot ? `<a href="${req.screenshot}" target="_blank"><img src="${req.screenshot}"></a>` : '<p>ስክሪንሻት የለም</p>'}
                                <br>
                                <button class="btn" onclick="approveDeposit(${req.id})">Approve (አረጋግጥ)</button>
                            </div>
                        `;
                    });
                }
            });

            fetch('/api/admin/users')
            .then(res => res.json())
            .then(data => {
                const container = document.getElementById('users-container');
                if(data.users.length === 0) {
                    container.innerHTML = 'ምንም ተመዝጋቢ የለም።';
                } else {
                    container.innerHTML = '';
                    data.users.forEach(u => {
                        container.innerHTML += `
                            <div class="user-row">
                                <span>📱 <b>${u.phone}</b></span>
                                <span style="color:#ff9800;">💰 <b>${u.balance} ETB</b></span>
                            </div>
                        `;
                    });
                }
            });
        }

        function approveDeposit(reqId) {
            fetch('/api/admin/approve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ req_id: reqId })
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                loadAdminData();
            });
        }

        loadAdminData();
        setInterval(loadAdminData, 5000);
    </script>
</body>
</html>
"""

# --- BACKEND API ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_TEMPLATE)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    phone = data.get('phone')
    if not phone:
        return jsonify({"success": False, "message": "ስልክ ቁጥር አልተገኘም!"})

    if phone not in users:
        users[phone] = {"phone": phone, "balance": 0.0}

    return jsonify({"success": True, "balance": users[phone]["balance"]})

@app.route('/api/get_user', methods=['GET'])
def get_user():
    phone = request.args.get('phone')
    if phone in users:
        return jsonify({"success": True, "balance": users[phone]["balance"]})
    return jsonify({"success": False}), 404

@app.route('/api/deposit', methods=['POST'])
def deposit():
    data = request.json
    phone = data.get('phone')
    amount = float(data.get('amount', 0))
    screenshot = data.get('screenshot', '')

    req_id = len(deposit_requests) + 1
    deposit_requests.append({
        "id": req_id,
        "phone": phone,
        "amount": amount,
        "screenshot": screenshot,
        "status": "pending"
    })
    return jsonify({"success": True, "message": "የክፍያ ማረጋገጫዎ ለአድሚን ተልኳል! ሲታረም ባላንስዎ ይጨመራል።"})

@app.route('/api/admin/requests', methods=['GET'])
def admin_requests():
    pending = [r for r in deposit_requests if r["status"] == "pending"]
    return jsonify({"requests": pending})

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    all_users = list(users.values())
    return jsonify({"users": all_users})

@app.route('/api/admin/approve', methods=['POST'])
def admin_approve():
    data = request.json
    req_id = data.get('req_id')

    for req in deposit_requests:
        if req["id"] == req_id and req["status"] == "pending":
            req["status"] = "approved"
            phone = req["phone"]
            amount = req["amount"]
            if phone in users:
                users[phone]["balance"] += amount
            return jsonify({"success": True, "message": "በስኬት አጸድቀዋል! ብሩ ተደምሯል።"})

    return jsonify({"success": False, "message": "ጥያቄው አልተገኘም!"}), 404

@app.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.json
    phone = data.get('phone')
    room_id = data.get('room_id')

    user = users.get(phone)
    room = rooms.get(room_id)

    if not user or not room:
        return jsonify({"success": False, "message": "መረጃው አልተገኘም!"}), 404

    if user['balance'] < room['entry_fee']:
        return jsonify({"success": False, "message": f"በቂ ባላንስ የለዎትም! (የሚጠበቀው: {room['entry_fee']} ብር፣ ያሎት: {user['balance']} ብር)"}), 400

    if phone in room['players']:
        return jsonify({"success": True, "message": "ቀድመው ገብተዋል!", "balance": user['balance']})

    room['players'].append(phone)

    if len(room['players']) == room['max_players']:
        room['status'] = "playing"
        for p in room['players']:
            users[p]['balance'] -= room['entry_fee']

    return jsonify({"success": True, "message": "ክፍሉን ተቀላቅለዋል!", "balance": user['balance']})

@app.route('/api/claim_bingo', methods=['POST'])
def claim_bingo():
    data = request.json
    phone = data.get('phone')
    room_id = data.get('room_id')
    room = rooms.get(room_id)
    user = users.get(phone)

    if not room or not user:
        return jsonify({"success": False, "message": "ስህተት ተፈጥሯል!"}), 400

    total_pool = room['entry_fee'] * room['max_players']
    winner_prize = total_pool * 0.75
    user['balance'] += winner_prize
    room['status'] = "finished"

    return jsonify({"success": True, "message": f"🎉 BINGO! {winner_prize} ብር ባላንስዎ ላይ ተደምሯል!", "new_balance": user['balance']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
