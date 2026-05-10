from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy

import random
import json

from io import BytesIO

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Paragraph
from reportlab.platypus import Spacer

from reportlab.lib.styles import getSampleStyleSheet

from questions import questions

app = Flask(__name__)

app.secret_key = 'nkgwete_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assessment.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

DB = SQLAlchemy(app)


# =========================================
# USER MODEL
# =========================================

class User(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    username = DB.Column(DB.String(100), unique=True)

    password = DB.Column(DB.String(300))

    role = DB.Column(DB.String(100))

    region = DB.Column(DB.String(100))


# =========================================
# CANDIDATE MODEL
# =========================================

class Candidate(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    fullname = DB.Column(DB.String(200))
    email = DB.Column(DB.String(200))
    phone = DB.Column(DB.String(50))
    city = DB.Column(DB.String(100))

    region = DB.Column(DB.String(100))

    experience = DB.Column(DB.String(50))
    license = DB.Column(DB.String(10))
    vehicle = DB.Column(DB.String(10))

    score = DB.Column(DB.Integer)

    result = DB.Column(DB.String(100))

    answers = DB.Column(DB.Text)


with app.app_context():

    DB.create_all()

    # CREATE DEFAULT ADMIN

    admin_exists = User.query.filter_by(
        username='admin'
    ).first()

    if not admin_exists:

        admin = User(

            username='admin',

            password=generate_password_hash(
                'Nkgwete123'
            ),

            role='Super Admin',

            region='All'

        )

        DB.session.add(admin)

        DB.session.commit()


# =========================================
# HOME PAGE
# =========================================

@app.route('/')
def index():
    return render_template('index.html')


# =========================================
# REGISTER PAGE
# =========================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        candidate = Candidate(

            fullname=request.form['fullname'],
            email=request.form['email'],
            phone=request.form['phone'],

            city=request.form['city'],
            region=request.form['region'],

            experience=request.form['experience'],
            license=request.form['license'],
            vehicle=request.form['vehicle'],

            score=0,
            result="",
            answers=""

        )

        DB.session.add(candidate)

        DB.session.commit()

        session['candidate_id'] = candidate.id

        random_questions = random.sample(
            questions,
            min(50, len(questions))
        )

        session['questions'] = random_questions

        return redirect('/test')

    return render_template('register.html')


# =========================================
# TEST PAGE
# =========================================

@app.route('/test', methods=['GET', 'POST'])
def test():

    stored_questions = session.get('questions', [])

    if request.method == 'POST':

        score = 0

        candidate_answers = []

        for i, q in enumerate(stored_questions):

            selected = request.form.get(f'q{i}')

            candidate_answers.append({

                "question": q['question'],
                "selected": selected,
                "correct": q['answer']

            })

            if selected == q['answer']:
                score += 1

        # RESULT LOGIC

        if score >= 45:
            result = "PERFECT FIT"

        elif score >= 35:
            result = "OKAY - NEEDS WORK"

        else:
            result = "DO NOT EMPLOY"

        candidate_id = session.get('candidate_id')

        candidate = Candidate.query.get(candidate_id)

        if candidate:

            candidate.score = score

            candidate.result = result

            candidate.answers = json.dumps(candidate_answers)

            DB.session.commit()

        return redirect('/thankyou')

    return render_template(
        'test.html',
        questions=stored_questions
    )


# =========================================
# THANK YOU PAGE
# =========================================

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')


# =========================================
# LOGIN
# =========================================

@app.route('/admin', methods=['GET', 'POST'])
def admin():

    error = None

    if request.method == 'POST':

        username = request.form['username']

        password = request.form['password']

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session['user_id'] = user.id

            session['role'] = user.role

            session['region'] = user.region

            return redirect('/dashboard')

        else:

            error = "Invalid Login"

    return render_template(
        'admin_login.html',
        error=error
    )


# =========================================
# DASHBOARD
# =========================================

@app.route('/dashboard')
def dashboard():

    if not session.get('user_id'):
        return redirect('/admin')

    role = session.get('role')

    region = session.get('region')

    if role == 'Super Admin':

        candidates = Candidate.query.order_by(
            Candidate.score.desc()
        ).all()

    else:

        candidates = Candidate.query.filter_by(
            region=region
        ).order_by(
            Candidate.score.desc()
        ).all()

    return render_template(
        'admin_dashboard.html',
        candidates=candidates,
        role=role
    )


# =========================================
# CREATE USER
# =========================================

@app.route('/create-user', methods=['GET', 'POST'])
def create_user():

    if session.get('role') != 'Super Admin':
        return redirect('/dashboard')

    success = None

    if request.method == 'POST':

        username = request.form['username']

        password = request.form['password']

        role = request.form['role']

        region = request.form['region']

        user = User(

            username=username,

            password=generate_password_hash(
                password
            ),

            role=role,

            region=region

        )

        DB.session.add(user)

        DB.session.commit()

        success = "User created successfully"

    return render_template(
        'create_user.html',
        success=success
    )


# =========================================
# RESET PASSWORD
# =========================================

@app.route('/reset-password/<int:id>')
def reset_password(id):

    if session.get('role') != 'Super Admin':
        return redirect('/dashboard')

    user = User.query.get_or_404(id)

    user.password = generate_password_hash(
        'Temp1234'
    )

    DB.session.commit()

    return redirect('/users')


# =========================================
# USERS PAGE
# =========================================

@app.route('/users')
def users():

    if session.get('role') != 'Super Admin':
        return redirect('/dashboard')

    users = User.query.all()

    return render_template(
        'users.html',
        users=users
    )


# =========================================
# DELETE CANDIDATE
# =========================================

@app.route('/delete/<int:id>')
def delete_candidate(id):

    if not session.get('user_id'):
        return redirect('/admin')

    candidate = Candidate.query.get_or_404(id)

    DB.session.delete(candidate)

    DB.session.commit()

    return redirect('/dashboard')


# =========================================
# PDF REPORT
# =========================================

@app.route('/report/<int:id>')
def report(id):

    if not session.get('user_id'):
        return redirect('/admin')

    candidate = Candidate.query.get_or_404(id)

    answers = json.loads(candidate.answers)

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    content = []

    content.append(

        Paragraph(
            "Nkgwete Field Engineer Assessment Report",
            styles['Title']
        )

    )

    content.append(Spacer(1, 20))

    content.append(
        Paragraph(
            f"<b>Candidate:</b> {candidate.fullname}",
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f"<b>Email:</b> {candidate.email}",
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f"<b>Phone:</b> {candidate.phone}",
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f"<b>Region:</b> {candidate.region}",
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f"<b>Score:</b> {candidate.score}/50",
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f"<b>Recommendation:</b> {candidate.result}",
            styles['BodyText']
        )
    )

    content.append(Spacer(1, 20))

    for i, a in enumerate(answers):

        content.append(
            Paragraph(
                f"<b>Question {i+1}:</b> {a['question']}",
                styles['BodyText']
            )
        )

        content.append(
            Paragraph(
                f"<b>Candidate Answer:</b> {a['selected']}",
                styles['BodyText']
            )
        )

        content.append(
            Paragraph(
                f"<b>Correct Answer:</b> {a['correct']}",
                styles['BodyText']
            )
        )

        content.append(Spacer(1, 10))

    doc.build(content)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{candidate.fullname}_assessment.pdf",
        mimetype='application/pdf'
    )


# =========================================
# LOGOUT
# =========================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)