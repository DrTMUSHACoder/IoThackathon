import os
import smtplib
import re
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, jsonify, session

app = Flask(__name__)
app.secret_key = 'prakalp-secure-iot-key-2026'

# 🌐 UNIVERSAL EMAIL VALIDATOR
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# ==============================
# 🔐 CONFIG
# ==============================
SENDER_EMAIL = 'hod-cse-iot@rcee.ac.in'
SENDER_PASSWORD = 'bichovbjfzkqypmh'

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# Database Connection (Vercel Postgres / Neon)
def get_db_connection():
    conn_url = os.environ.get('POSTGRES_URL') or os.environ.get('STORAGE_URL')
    if not conn_url:
        return None
    try:
        return psycopg2.connect(conn_url, sslmode='require')
    except:
        return None

# ==============================
# 📊 SCHEMA & METADATA
# ==============================
SCORING_FIELDS = {
    'R1':   ['r1_innovation', 'r1_problemrelevance', 'r1_techfeasibility', 'r1_claritypresentation'],
    'R2':   ['r2_feasibilityvalidation', 'r2_systemdesignlogic', 'r2_demoquality', 'r2_technicalunderstanding'],
    'R3P1': ['r3p1_initialimplementation', 'r3p1_approachmethodology', 'r3p1_progresslevel', 'r3p1_teamcoordination'],
    'R3P2': ['r3p2_improvementphase1', 'r3p2_innovationmodification', 'r3p2_problemsolvingapproach', 'r3p2_stabilityfunctionality'],
    'R4':   ['r4_innovation', 'r4_workingprototype', 'r4_realtimeimpact', 'r4_presentationskills', 'r4_qahandling']
}

SCORING_META = {
    'R1': {
        'title': 'Round 1 – Idea Submission',
        'desc': 'PPT submission + 3–5 min pitch to judges',
        'weight': '15%',
        'criteria': [
            {'field': 'r1_innovation',            'label': 'Innovation',              'max': 15},
            {'field': 'r1_problemrelevance',       'label': 'Problem Relevance',       'max': 10},
            {'field': 'r1_techfeasibility',        'label': 'Technical Feasibility',   'max': 15},
            {'field': 'r1_claritypresentation',    'label': 'Clarity of Presentation', 'max': 10},
        ]
    },
    'R2': {
        'title': 'Round 2 – Concept Validation',
        'desc': 'Simulation or architecture demonstration',
        'weight': '15%',
        'criteria': [
            {'field': 'r2_feasibilityvalidation',     'label': 'Feasibility Validation',    'max': 20},
            {'field': 'r2_systemdesignlogic',         'label': 'System Design & Logic',     'max': 15},
            {'field': 'r2_demoquality',               'label': 'Demonstration Quality',     'max': 10},
            {'field': 'r2_technicalunderstanding',    'label': 'Technical Understanding',   'max':  5},
        ]
    },
    'R3P1': {
        'title': 'Round 3 – Phase 1',
        'desc': 'Prototype development begins',
        'weight': '20%',
        'criteria': [
            {'field': 'r3p1_initialimplementation',  'label': 'Initial Implementation',   'max': 20},
            {'field': 'r3p1_approachmethodology',    'label': 'Approach & Methodology',   'max': 10},
            {'field': 'r3p1_progresslevel',          'label': 'Progress Level',           'max': 10},
            {'field': 'r3p1_teamcoordination',       'label': 'Team Coordination',        'max': 10},
        ]
    },
    'R3P2': {
        'title': 'Round 3 – Phase 2',
        'desc': 'Implementation of Modification 2',
        'weight': '20%',
        'criteria': [
            {'field': 'r3p2_improvementphase1',         'label': 'Improvement from Phase 1',    'max': 15},
            {'field': 'r3p2_innovationmodification',    'label': 'Innovation in Modification',  'max': 15},
            {'field': 'r3p2_problemsolvingapproach',    'label': 'Problem-Solving Approach',    'max': 10},
            {'field': 'r3p2_stabilityfunctionality',    'label': 'Stability & Functionality',   'max': 10},
        ]
    },
    'R4': {
        'title': 'Round 4 – Final Pitch',
        'desc': 'Presentation, live demo & Q&A',
        'weight': '30%',
        'criteria': [
            {'field': 'r4_innovation',          'label': 'Innovation',                    'max': 10},
            {'field': 'r4_workingprototype',    'label': 'Working Prototype',             'max': 15},
            {'field': 'r4_realtimeimpact',      'label': 'Real-Time Application Impact',  'max': 10},
            {'field': 'r4_presentationskills',  'label': 'Presentation Skills',           'max':  5},
            {'field': 'r4_qahandling',          'label': 'Q&A Handling',                  'max': 10},
        ]
    }
}

# ==============================
# 📥 DB INITIALIZATION (SQL)
# ==============================
def initialize_db(registry_path=None):
    conn = get_db_connection()
    if not conn: return
    
    try:
        cur = conn.cursor()
        # 1. Create table with scoring columns
        cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            TeamID TEXT PRIMARY KEY, ProjectID TEXT, TeamName TEXT, ProjectTitle TEXT, Email TEXT,
            r1_innovation NUMERIC DEFAULT 0, r1_problemrelevance NUMERIC DEFAULT 0, r1_techfeasibility NUMERIC DEFAULT 0, r1_claritypresentation NUMERIC DEFAULT 0,
            r2_feasibilityvalidation NUMERIC DEFAULT 0, r2_systemdesignlogic NUMERIC DEFAULT 0, r2_demoquality NUMERIC DEFAULT 0, r2_technicalunderstanding NUMERIC DEFAULT 0,
            r3p1_initialimplementation NUMERIC DEFAULT 0, r3p1_approachmethodology NUMERIC DEFAULT 0, r3p1_progresslevel NUMERIC DEFAULT 0, r3p1_teamcoordination NUMERIC DEFAULT 0,
            r3p2_improvementphase1 NUMERIC DEFAULT 0, r3p2_innovationmodification NUMERIC DEFAULT 0, r3p2_problemsolvingapproach NUMERIC DEFAULT 0, r3p2_stabilityfunctionality NUMERIC DEFAULT 0,
            r4_innovation NUMERIC DEFAULT 0, r4_workingprototype NUMERIC DEFAULT 0, r4_realtimeimpact NUMERIC DEFAULT 0, r4_presentationskills NUMERIC DEFAULT 0, r4_qahandling NUMERIC DEFAULT 0
        );
        """)
        
        if registry_path:
            cur.execute("DELETE FROM teams;")
            df = pd.read_csv(registry_path, sep=None, engine='python', encoding_errors='ignore') if registry_path.endswith('.csv') else pd.read_excel(registry_path)
            df.columns = [str(c).strip() for c in df.columns]
            for row in df.to_dict(orient='records'):
                def f(ks):
                    for k in ks:
                        for rk in row.keys():
                            if str(k).lower().replace("_","").replace(" ","") == str(rk).lower().replace("_","").replace(" ",""): return row[rk]
                    return ""
                e = str(f(['Email', 'MailId', 'LeaderEmail'])).strip()
                if "@" in e:
                    cur.execute("INSERT INTO teams (TeamID, ProjectID, TeamName, ProjectTitle, Email) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING;",
                               (str(f(['SNo', 'TeamID'])), str(f(['BatchNO', 'ProjectID'])), str(f(['TeamName', 'Name'])), str(f(['ProblemStatement', 'ProjectTitle'])), e))
        conn.commit()
    finally:
        if conn: conn.close()

def get_teams():
    conn = get_db_connection()
    if not conn: return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM teams;")
        teams = cur.fetchall()
        
        results = []
        for row in teams:
            row = dict(row)
            for k, v in row.items():
                if k.startswith('r'): row[k] = float(v or 0)
            def s(fs): return sum(float(row.get(f, 0)) for f in fs)
            row['R1_Total'] = s(SCORING_FIELDS['R1'])
            row['R2_Total'] = s(SCORING_FIELDS['R2'])
            row['R3P1_Total'] = s(SCORING_FIELDS['R3P1'])
            row['R3P2_Total'] = s(SCORING_FIELDS['R3P2'])
            row['R4_Total'] = s(SCORING_FIELDS['R4'])
            row['Weighted_Total'] = (row['R1_Total']*0.3) + (row['R2_Total']*0.3) + (row['R3P1_Total']*0.4) + (row['R3P2_Total']*0.4) + (row['R4_Total']*0.6)
            results.append(row)
        return sorted(results, key=lambda x: x['Weighted_Total'], reverse=True)
    except Exception as e:
        if 'does not exist' in str(e).lower():
            initialize_db()
        return []
    finally:
        if conn: conn.close()

# ==============================
# 📧 ENGINE & ROUTES
# ==============================
def send_real_email(to_email, subject, body):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = f"PRAKALP 2026 <{SENDER_EMAIL}>"
        msg['To'] = to_email.strip()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
    except: pass

@app.route('/')
def index():
    return render_template('index.html', teams=get_teams())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    return render_template('admin.html', teams=get_teams(), fields=SCORING_FIELDS, meta=SCORING_META)

@app.route('/update_scores', methods=['POST'])
def update_scores():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    form_data = request.form.to_dict()
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin'))
    try:
        cur = conn.cursor()
        for sno in set([k.split('_')[-1] for k in form_data.keys() if '_' in k]):
            up, pa = [], []
            for m, fs in SCORING_FIELDS.items():
                for f in fs:
                    if f"f_{sno}" in form_data: # Placeholder
                        pass
                    if f"{f}_{sno}" in form_data:
                        up.append(f"{f} = %s")
                        pa.append(float(form_data[f"{f}_{sno}"] or 0))
            if up:
                pa.append(sno)
                cur.execute(f"UPDATE teams SET {', '.join(up)} WHERE TeamID = %s", pa)
        conn.commit()
    finally: conn.close()
    return redirect(url_for('admin') + '?saved=1')

@app.route('/upload_dispatch', methods=['POST'])
def upload_dispatch():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    file = request.files.get('registry_file')
    if not file: return redirect(url_for('admin'))
    path = os.path.join('/tmp', 'registry.csv')
    file.save(path)
    df = pd.read_csv(path, sep=None, engine='python', encoding_errors='ignore')
    rows = df.to_dict(orient='records')
    sent = 0
    for row in rows:
        def f(ks):
            for k in ks:
                for rk in row.keys():
                    if str(k).lower().replace(" ","") == str(rk).lower().replace(" ",""): return row[rk]
            return ""
        email = str(f(['Email', 'MailId'])).strip()
        if "@" in email:
            pid, name, title = f(['ProjectID', 'Batch NO']), f(['TeamName', 'Name']), f(['ProjectTitle', 'Problem'])
            body = f"Dear Student {name},\n\nYour problem statement: {title}\nProject ID: {pid}\n\nGood luck!"
            send_real_email(email, f"PRAKALP Assignment: {pid}", body)
            sent += 1
    return redirect(url_for('admin') + f'?emailed=1&sent={sent}&step1_done=1&tab=setup')

@app.route('/finalize_registry', methods=['POST'])
def finalize_registry():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    path = os.path.join('/tmp', 'registry.csv')
    if os.path.exists(path): initialize_db(path)
    return redirect(url_for('admin') + '?registered=1&tab=setup')

@app.route('/reset_db', methods=['POST'])
def reset_db():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    initialize_db()
    return redirect(url_for('admin') + '?reset=1')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)