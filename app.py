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
from reportlab.platypus import Image

# =========================================
# APP CONFIG
# =========================================

app = Flask(__name__)

app.secret_key = 'gtba_talent_secret_key'

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
# POSITION MODEL
# =========================================

class Position(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    name = DB.Column(DB.String(200), unique=True)


# =========================================
# QUESTION MODEL
# =========================================

class Question(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    position_id = DB.Column(DB.Integer)

    question = DB.Column(DB.Text)

    option1 = DB.Column(DB.String(300))
    option2 = DB.Column(DB.String(300))
    option3 = DB.Column(DB.String(300))
    option4 = DB.Column(DB.String(300))

    answer = DB.Column(DB.String(300))

    qtype = DB.Column(DB.String(100))


# =========================================
# CANDIDATE MODEL
# =========================================

class Candidate(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    fullname = DB.Column(DB.String(200))

    email = DB.Column(DB.String(200))

    phone = DB.Column(DB.String(100))

    city = DB.Column(DB.String(100))

    region = DB.Column(DB.String(100))

    position = DB.Column(DB.String(200))

    experience = DB.Column(DB.String(100))

    license = DB.Column(DB.String(20))

    vehicle = DB.Column(DB.String(20))

    score = DB.Column(DB.Integer)

    result = DB.Column(DB.String(100))

    answers = DB.Column(DB.Text)


# =========================================
# CREATE DATABASE
# =========================================

with app.app_context():

    DB.create_all()

    admin_exists = User.query.filter_by(
        username='admin'
    ).first()

    if not admin_exists:

        admin = User(

            username='admin',

            password=generate_password_hash(
                'GTBAAdmin2026'
            ),

            role='Super Admin',

            region='All'

        )

        DB.session.add(admin)

        DB.session.commit()


# =========================================
# HOME
# =========================================

@app.route('/')
def index():

    return render_template('index.html')


# =========================================
# REGISTER
# =========================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    positions = Position.query.all()

    if request.method == 'POST':

        candidate = Candidate(

            fullname=request.form['fullname'],
            email=request.form['email'],
            phone=request.form['phone'],
            city=request.form['city'],

            region=request.form['region'],

            position=request.form['position'],

            experience=request.form['experience'],

            license=request.form['license'],

            vehicle=request.form['vehicle'],

            score=0,

            result='',

            answers=''

        )

        DB.session.add(candidate)

        DB.session.commit()

        session['candidate_id'] = candidate.id

        selected_position = Position.query.filter_by(
            name=request.form['position']
        ).first()

        question_list = Question.query.filter_by(
            position_id=selected_position.id
        ).all()

        questions = []

        for q in question_list:

            questions.append({

                'question': q.question,

                'options': [
                    q.option1,
                    q.option2,
                    q.option3,
                    q.option4
                ],

                'answer': q.answer,

                'type': q.qtype

            })

        random_questions = random.sample(
            questions,
            min(50, len(questions))
        )

        session['questions'] = random_questions

        return redirect('/test')

    return render_template(
        'register.html',
        positions=positions
    )


# =========================================
# TEST
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

                'question': q['question'],

                'selected': selected,

                'correct': q['answer']

            })

            if selected == q['answer']:

                score += 1

        if score >= 45:

            result = 'PERFECT FIT'

        elif score >= 35:

            result = 'OKAY - NEEDS WORK'

        else:

            result = 'DO NOT EMPLOY'

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
# THANK YOU
# =========================================

@app.route('/thankyou')
def thankyou():

    return render_template('thankyou.html')


# =========================================
# ADMIN LOGIN
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

            error = 'Invalid Login'

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
# USERS
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
# CREATE USER
# =========================================

@app.route('/create-user', methods=['GET', 'POST'])
def create_user():

    if session.get('role') != 'Super Admin':

        return redirect('/dashboard')

    success = None

    if request.method == 'POST':

        username = request.form['username']

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            success = 'Username already exists'

        else:

            user = User(

                username=username,

                password=generate_password_hash(
                    request.form['password']
                ),

                role=request.form['role'],

                region=request.form['region']

            )

            DB.session.add(user)

            DB.session.commit()

            success = 'User created successfully'

    return render_template(
        'create_user.html',
        success=success
    )


# =========================================
# RESET PASSWORD
# =========================================

@app.route('/reset-password/<int:id>', methods=['POST'])
def reset_password(id):

    if session.get('role') != 'Super Admin':

        return redirect('/dashboard')

    user = User.query.get_or_404(id)

    user.password = generate_password_hash(
        request.form['password']
    )

    DB.session.commit()

    return redirect('/users')


# =========================================
# DELETE USER
# =========================================

@app.route('/delete-user/<int:id>')
def delete_user(id):

    if session.get('role') != 'Super Admin':

        return redirect('/dashboard')

    user = User.query.get_or_404(id)

    DB.session.delete(user)

    DB.session.commit()

    return redirect('/users')


# =========================================
# POSITIONS
# =========================================

@app.route('/positions', methods=['GET', 'POST'])
def positions():

    if session.get('role') != 'Super Admin':

        return redirect('/dashboard')

    if request.method == 'POST':

        position = Position(
            name=request.form['name']
        )

        DB.session.add(position)

        DB.session.commit()

    positions = Position.query.all()

    return render_template(
        'positions.html',
        positions=positions
    )


# =========================================
# MANAGE QUESTIONS
# =========================================

@app.route('/questions/<int:position_id>', methods=['GET', 'POST'])
def manage_questions(position_id):

    if session.get('role') != 'Super Admin':

        return redirect('/dashboard')

    position = Position.query.get_or_404(position_id)

    if request.method == 'POST':

        question = Question(

            position_id=position_id,

            question=request.form['question'],

            option1=request.form['option1'],
            option2=request.form['option2'],
            option3=request.form['option3'],
            option4=request.form['option4'],

            answer=request.form['answer'],

            qtype=request.form['qtype']

        )

        DB.session.add(question)

        DB.session.commit()

    questions = Question.query.filter_by(
        position_id=position_id
    ).all()

    return render_template(
        'manage_questions.html',
        questions=questions,
        position=position
    )


# =========================================
# EDIT QUESTION
# =========================================

@app.route('/edit-question/<int:id>', methods=['GET', 'POST'])
def edit_question(id):

    if session.get('role') != 'Super Admin':

        return redirect('/dashboard')

    question = Question.query.get_or_404(id)

    if request.method == 'POST':

        question.question = request.form['question']

        question.option1 = request.form['option1']
        question.option2 = request.form['option2']
        question.option3 = request.form['option3']
        question.option4 = request.form['option4']

        question.answer = request.form['answer']

        question.qtype = request.form['qtype']

        DB.session.commit()

        return redirect(f'/questions/{question.position_id}')

    return render_template(
        'edit_question.html',
        question=question
    )


# =========================================
# DELETE QUESTION
# =========================================

@app.route('/delete-question/<int:id>')
def delete_question(id):

    if session.get('role') != 'Super Admin':

        return redirect('/dashboard')

    question = Question.query.get_or_404(id)

    position_id = question.position_id

    DB.session.delete(question)

    DB.session.commit()

    return redirect(f'/questions/{position_id}')


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
    #LOGO
    logo = Image('static/gtba_logo.png' )
    logo.drawHeight=140
    logo.drawWidth=140
    content.append(logo)
    content.append(Spacer(1,15))

    content.append(
    Paragraph(
        'Confidential Candidate Assessment Report',
        styles['Title']
    )
)

    content.append(Spacer(1, 20))
    content.append(
        Paragraph(
            'GTBA Talent Platform Assessment Report',
            styles['Title']
        )
    )

    content.append(Spacer(1, 20))

    content.append(
        Paragraph(
            f'<b>Candidate:</b> {candidate.fullname}',
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f'<b>Position:</b> {candidate.position}',
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f'<b>Region:</b> {candidate.region}',
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f'<b>Score:</b> {candidate.score}/50',
            styles['BodyText']
        )
    )

    content.append(
        Paragraph(
            f'<b>Recommendation:</b> {candidate.result}',
            styles['BodyText']
        )
    )

    content.append(Spacer(1, 20))

    for i, a in enumerate(answers):

        content.append(
            Paragraph(
                f'<b>Question {i+1}:</b> {a["question"]}',
                styles['BodyText']
            )
        )

        content.append(
            Paragraph(
                f'<b>Candidate Answer:</b> {a["selected"]}',
                styles['BodyText']
            )
        )

        content.append(
            Paragraph(
                f'<b>Correct Answer:</b> {a["correct"]}',
                styles['BodyText']
            )
        )

        content.append(Spacer(1, 10))

    doc.build(content)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'{candidate.fullname}_assessment.pdf',
        mimetype='application/pdf'
    )


# =========================================
# LOGOUT
# =========================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# =========================================
# RUN APP
# =========================================

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)