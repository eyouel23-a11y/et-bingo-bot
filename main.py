import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, template_folder='template')
app.secret_key = 'your_secret_key_here'

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bingo_game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Model (ዳታቤዝ ቴብል)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# Database-ውን መፍጠር
with app.app_context():
    db.create_all()

# Home / Index Route
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

# Rooms Route
@app.route('/rooms')
def rooms():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('rooms.html', username=session['username'])

# Games Route
@app.route('/games')
def games():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('games.html', username=session['username'])

# Account Route
@app.route('/account')
def account():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    return render_template('account.html', user=user)

# Admin Route
@app.route('/admin')
def admin():
    if 'username' not in session:
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('admin.html', users=users)

# Login / Register Route (ባለ አንድ ፔጅ የተስተካከለ ሎጂክ)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        phone = request.form.get('phone', '')
        password = request.form.get('password')
        
        # ተጠቃሚው ዳታቤዝ ውስጥ መኖሩን እንፈትሻለን
        user = User.query.filter_by(username=username).first()
        
        if user:
            # ቀድሞ የተመዘገበ ከሆነ ፓስወርዱን እናረጋግጣለን
            if user.password == password:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="የገባው ፓስወርድ ስህተት ነው!")
        else:
            # አዲስ ተጠቃሚ ከሆነ በአዲስ መልክ ዳታቤዝ ውስጥ እንመዝግበዋለን
            new_user = User(username=username, phone=phone, password=password)
            db.session.add(new_user)
            db.session.commit()
            
            session['username'] = username
            return redirect(url_for('index'))
            
    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
