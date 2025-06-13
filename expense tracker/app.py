from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secretkey'

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'expenses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            category = request.form['category']
            description = request.form['description']
            date_str = request.form['date']
            date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.utcnow()

            expense = Expense(
                amount=amount,
                category=category,
                description=description,
                date=date,
                user_id=current_user.id
            )
            db.session.add(expense)
            db.session.commit()
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error adding expense: {e}')
            return redirect(url_for('dashboard'))

    filter_type = request.args.get('filter')
    query = Expense.query.filter_by(user_id=current_user.id)
    now = datetime.utcnow()

    if filter_type == 'monthly':
        query = query.filter(
            db.extract('month', Expense.date) == now.month,
            db.extract('year', Expense.date) == now.year
        )
    elif filter_type == 'yearly':
        query = query.filter(
            db.extract('year', Expense.date) == now.year
        )

    expenses = query.order_by(Expense.date.desc()).all()
    total_amount = sum(exp.amount for exp in expenses)

    return render_template(
        'dashboard.html',
        expenses=expenses,
        total_amount=total_amount,
        filter_type=filter_type
    )

if __name__ == '__main__':
    app.run(debug=True)
