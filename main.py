import os
import random
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# --- HTML TEMPLATE INLINED TO PREVENT FOLDER ERRORS ---
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
        .header-card { background: var(--card-bg); padding: 15px; border-radius: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
        .balance-box { font-size: 18px; font-weight: bold; color: var(--accent-color); }
        .section-title { font-size: 16px; margin: 15px 0 10px 0; text-align: left; border-left: 4px solid var(--accent-color); padding-left: 8px; }
        .rooms-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .room-card { background: var(--card-bg); border: 1px solid #333; border-radius: 10px; padding: 12px; text-align: center; }
        .room-card h4 { margin: 0 0 5px 0; }
        .room-card p { margin: 0 0 8px 0; font-size: 12px; color: #aaa; }
        .btn { background-color: var(--btn-blue); color: white; border: none; padding: 10px; font-size: 14px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        .btn-success { background-color: var(--btn-green); }
        .btn-danger { background-color: var(--btn-red); }
        .btn-bingo { background-color: var(--accent-color); font-size: 20px; padding: 15px; margin-top: 15px; }
        .bingo-board { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; max-width: 350px; margin: 15px auto; background: #2a2a2a; padding: 8px; border-radius: 10px; }
        .bingo-cell { background: #1e1e1e; border: 1px solid #444; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; border-radius: 6px; cursor: pointer; }
        .bingo-cell.marked { background-color: var(--btn-green); color: white; }
        .bingo-cell.free { background-color: var(--accent-color); color: black; font-size: 12px; }
        .telebirr-box { background: var(--card-bg); padding: 15px; border-radius: 10px; margin-top: 15px; }
        input { width: 90%; padding: 10px; margin: 6px 0; border-radius: 6px; border: 1px solid #444; background: #121212; color: white; }
    </style>
</head>
<body>
    <div class="header-card">
        <div><b>🎲 ET BINGO</b></div>
        <div class="balance-box">💰 <span id="balance">100.00</span> ETB</div>
    </div>

    <div id="game-section" style="display:none;">
        <div style="background:#222; padding:10px; border-radius:8px; font-size:18px;">ወጣ ገባ ቁጥር፦ <span id="current-drawn-num">-</span></div>
        <div class="bingo-board" id="bingo-board"></div>
        <button class="btn btn-bingo" onclick="claimBingo()">🎉 BINGO!</button>
    </div>

    <div id="rooms-section">
        <div class="section-title">የጨዋታ ክፍሎች (Auto Rooms)</div>
        <div class="rooms-grid">
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

    <div class="telebirr-box">
        <div class="section-title" style="margin-top:0;">📲 የቴሌብር ሂሳብ አስገባ/አውጣ</div>
        <input type="number" id="tb-amount" placeholder="የብር መጠን (ETB)">
        <input type="text" id="tb-txid" placeholder="Transaction ID / ስልክ">
        <div style="display: flex; gap: 8px; margin-top: 5px;">
            <button class="btn btn-success" onclick="depositTelebirr()">ብር አስገባ</button>
            <button class="btn btn-danger" onclick="withdrawTelebirr()">ብር አውጣ</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let currentRoomId = null;

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
                body: JSON.stringify({ user_id: 'user_1', room_id: roomId })
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                if(data.success) {
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
                body: JSON.stringify({ user_id: 'user_1', room_id: currentRoomId })
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

        function depositTelebirr() {
            const amt = document.getElementById('tb-amount').value;
            const tx = document.getElementById('tb-txid').value;
            if(!amt || !tx) return alert('መጠኑን እና Transaction ID ያስገቡ!');
            fetch('/api/deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: 'user_1', amount: amt, tx_id: tx })
            }).then(res => res.json()).then(data => alert(data.message));
        }

        function withdrawTelebirr() {
            const amt = document.getElementById('tb-amount').value;
            const tx = document.getElementById('tb-txid').value;
            if(!amt || !tx) return alert('መጠኑን እና ስልክ ቁጥር ያስገቡ!');
            fetch('/api/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: 'user_1', amount: amt, telebirr: tx })
            }).then(res => res.json()).then(data => alert(data.message));
        }
    </script>
</body>
</html>
"""

# --- IN-MEMORY DATABASE ---
users = {
    "user_1": {"name": "Player 1", "balance": 100.0, "telebirr": "0911000000"}
}

rooms = {
    "room_20_5": {"id": "room_20_5", "name": "ባለ 20 ብር (5 ሰው)", "entry_fee": 20, "max_players": 5, "players": [], "status": "waiting"},
    "room_30_5": {"id": "room_30_5", "name": "ባለ 30 ብር (5 ሰው)", "entry_fee": 30, "max_players": 5, "players": [], "status": "waiting"},
    "room_40_5": {"id": "room_40_5", "name": "ባለ 40 ብር (5 ሰው)", "entry_fee": 40, "max_players": 5, "players": [], "status": "waiting"},
    "room_30_10": {"id": "room_30_10", "name": "ባለ 30 ብር (10 ሰው)", "entry_fee": 30, "max_players": 10, "players": [], "status": "waiting"}
}

deposit_requests = []
withdrawal_requests = []

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.json
    user_id = data.get('user_id')
    room_id = data.get('room_id')
    user = users.get(user_id)
    room = rooms.get(room_id)

    if not user or not room:
        return jsonify({"success": False, "message": "መረጃው አልተገኘም!"}), 404

    if user['balance'] < room['entry_fee']:
        return jsonify({"success": False, "message": "ለዚህ ክፍል በቂ ባላንስ የለህም!"}), 400

    if user_id in room['players']:
        return jsonify({"success": True, "message": "ቀድመህ ገብተሃል!"})

    room['players'].append(user_id)

    if len(room['players']) == room['max_players']:
        room['status'] = "playing"
        for pid in room['players']:
            users[pid]['balance'] -= room['entry_fee']

    return jsonify({"success": True, "message": "ክፍሉን በስኬት ተቀላቅለሃል!"})

@app.route('/api/claim_bingo', methods=['POST'])
def claim_bingo():
    data = request.json
    user_id = data.get('user_id')
    room_id = data.get('room_id')
    room = rooms.get(room_id)
    user = users.get(user_id)

    total_pool = room['entry_fee'] * room['max_players']
    winner_prize = total_pool * 0.75
    user['balance'] += winner_prize

    return jsonify({"success": True, "message": f"🎉 BINGO! {winner_prize} ብር ተደምሮልሃል!", "new_balance": user['balance']})

@app.route('/api/deposit', methods=['POST'])
def deposit():
    data = request.json
    deposit_requests.append({"user_id": data.get('user_id'), "amount": float(data.get('amount')), "tx_id": data.get('tx_id')})
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
    withdrawal_requests.append({"user_id": user_id, "amount": amount, "telebirr": data.get('telebirr')})
    return jsonify({"success": True, "message": "የወጪ ጥያቄህ ተልኳል!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
