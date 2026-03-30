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

# Database Connection (Vercel Postgres)
def get_db_connection():
    conn_url = os.environ.get('POSTGRES_URL') or os.environ.get('STORAGE_URL')
    if not conn_url:
        # Fallback for local testing if needed
        raise Exception("Database Connection URL (POSTGRES_URL/STORAGE_URL) is missing!")
    return psycopg2.connect(conn_url, sslmode='require')

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
    cur = conn.cursor()
    
    # 1. Create table if not exists with all scoring columns
    create_table_query = """
    CREATE TABLE IF NOT EXISTS teams (
        TeamID TEXT PRIMARY KEY,
        ProjectID TEXT,
        TeamName TEXT,
        ProjectTitle TEXT,
        Email TEXT,
        r1_innovation NUMERIC DEFAULT 0,
        r1_problemrelevance NUMERIC DEFAULT 0,
        r1_techfeasibility NUMERIC DEFAULT 0,
        r1_claritypresentation NUMERIC DEFAULT 0,
        r2_feasibilityvalidation NUMERIC DEFAULT 0,
        r2_systemdesignlogic NUMERIC DEFAULT 0,
        r2_demoquality NUMERIC DEFAULT 0,
        r2_technicalunderstanding NUMERIC DEFAULT 0,
        r3p1_initialimplementation NUMERIC DEFAULT 0,
        r3p1_approachmethodology NUMERIC DEFAULT 0,
        r3p1_progresslevel NUMERIC DEFAULT 0,
        r3p1_teamcoordination NUMERIC DEFAULT 0,
        r3p2_improvementphase1 NUMERIC DEFAULT 0,
        r3p2_innovationmodification NUMERIC DEFAULT 0,
        r3p2_problemsolvingapproach NUMERIC DEFAULT 0,
        r3p2_stabilityfunctionality NUMERIC DEFAULT 0,
        r4_innovation NUMERIC DEFAULT 0,
        r4_workingprototype NUMERIC DEFAULT 0,
        r4_realtimeimpact NUMERIC DEFAULT 0,
        r4_presentationskills NUMERIC DEFAULT 0,
        r4_qahandling NUMERIC DEFAULT 0
    );
    """
    cur.execute(create_table_query)
    
    if registry_path:
        # Clear existing data for fresh initialization
        cur.execute("DELETE FROM teams;")
        
        # Load registry
        if registry_path.endswith('.csv'):
            df = pd.read_csv(registry_path, sep=None, engine='python', encoding_errors='ignore')
        else:
            df = pd.read_excel(registry_path)
            
        df.columns = [str(c).strip() for c in df.columns]
        rows = df.to_dict(orient='records')
        
        for row in rows:
            def find_val(keys):
                for k in keys:
                    for rk in row.keys():
                        if str(k).lower().strip().replace("_","").replace(" ","") == str(rk).lower().strip().replace("_","").replace(" ",""): return row[rk]
                return ""

            email = str(find_val(['Email', 'MailId', 'EmailID', 'Mail Id', 'LeaderEmail'])).strip()
            if not email or "@" not in email or "placeholder" in email: continue

            insert_query = """
            INSERT INTO teams (TeamID, ProjectID, TeamName, ProjectTitle, Email)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (TeamID) DO NOTHING;
            """
            cur.execute(insert_query, (
                str(find_val(['SNo', 'TeamID', 'ID', 'S.No'])),
                str(find_val(['BatchNO', 'ProjectID', 'PID', 'Batch NO'])),
                str(find_val(['NameoftheStudent', 'TeamName', 'StudentName', 'Name', 'Name of The Student'])),
                str(find_val(['ProblemStatement', 'ProjectTitle', 'Title', 'ProblemStatement', 'Problem Statement'])),
                email
            ))
            
    conn.commit()
    cur.close()
    conn.close()

def get_teams():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM teams;")
    teams = cur.fetchall()
    
    results = []
    for row in teams:
        row = dict(row) # convert from RealDict to standard dict
        # Force numeric conversion for template safety
        for k, v in row.items():
            if k.startswith('r'): row[k] = float(v or 0)
            
        def sum_round(fields): return sum(float(row.get(f, 0)) for f in fields)
        row['R1_Total'] = sum_round(SCORING_FIELDS['R1'])
        row['R2_Total'] = sum_round(SCORING_FIELDS['R2'])
        row['R3P1_Total'] = sum_round(SCORING_FIELDS['R3P1'])
        row['R3P2_Total'] = sum_round(SCORING_FIELDS['R3P2'])
        row['R4_Total'] = sum_round(SCORING_FIELDS['R4'])
        
        row['Weighted_Total'] = (row['R1_Total'] * 0.3) + (row['R2_Total'] * 0.3) + (row['R3P1_Total'] * 0.4) + (row['R3P2_Total'] * 0.4) + (row['R4_Total'] * 0.6)
        row['Raw_Total'] = row['R1_Total'] + row['R2_Total'] + row['R3P1_Total'] + row['R3P2_Total'] + row['R4_Total']
        results.append(row)
        
    cur.close()
    conn.close()
    return sorted(results, key=lambda x: float(x['Weighted_Total']), reverse=True)

# ==============================
# 📧 EMAIL ENGINE
# ==============================
def send_real_email(to_email, subject, body):
    clean_addr = to_email.strip().replace(" ", "")
    if not clean_addr or "placeholder@example.com" in clean_addr or "@" not in clean_addr: return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = f"PRAKALP 2026 <{SENDER_EMAIL}>"
        msg['To'] = clean_addr
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[ERROR] Email Failed to {clean_addr}: {e}")

# ==============================
# 🌐 ROUTES
# ==============================
@app.route('/')
def index():
    try:
        return render_template('index.html', teams=get_teams())
    except: return render_template('index.html', teams=[])

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
    cur = conn.cursor()
    
    # Batch update implementation
    for sno in set([k.split('_')[-1] for k in form_data.keys() if '_' in k]):
        update_parts = []
        params = []
        for round_name, sub_fields in SCORING_FIELDS.items():
            for field in sub_fields:
                key = f"{field}_{sno}"
                if key in form_data:
                    update_parts.append(f"{field} = %s")
                    params.append(float(form_data[key] or 0))
        
        if update_parts:
            query = f"UPDATE teams SET {', '.join(update_parts)} WHERE TeamID = %s"
            params.append(sno)
            cur.execute(query, params)
            
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin') + '?saved=1')

@app.route('/upload_dispatch', methods=['POST'])
def upload_dispatch():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    file = request.files.get('registry_file')
    if not file: return redirect(url_for('admin') + '?error=no_file')

    ext = '.csv' if file.filename.endswith('.csv') else '.xlsx'
    temp_path = os.path.join('/tmp', f'latest_registry{ext}')
    file.save(temp_path)

    df = pd.read_csv(temp_path, sep=None, engine='python', encoding_errors='ignore') if ext == '.csv' else pd.read_excel(temp_path)
    df.columns = [str(c).strip() for c in df.columns]
    rows = df.to_dict(orient='records')
    
    sent, failed_list = 0, []
    for row in rows:
        def find_val(keys):
            for k in keys:
                for rk in row.keys():
                    if str(k).lower().strip().replace(" ","") == str(rk).lower().strip().replace(" ",""): return row[rk]
            return ""
        
        email = str(find_val(['Email', 'MailId', 'EmailID', 'Mail Id'])).strip()
        if not email or not EMAIL_REGEX.match(email):
            failed_list.append({'name': str(find_val(['TeamName', 'Name of The Student'])), 'email': email, 'reason': 'Invalid Format'})
            continue
            
        pid = find_val(['ProjectID', 'Batch NO'])
        name = str(find_val(['TeamName', 'Name of The Student'])).strip() or 'Unknown'
        title = find_val(['ProjectTitle', 'Problem Statement'])

        body = f"""Dear Student {name},

Greetings from PRAKALP IoT Hackathon Team!

We are pleased to inform you that your problem statement has been officially assigned for the PRAKALP IoT Hackathon.

Hackathon Project ID: {pid}
Problem Statement: "{title}"

You are requested to carefully go through the problem statement and start working on your project. Make sure to plan your approach, develop innovative solutions, and stay consistent with the given guidelines and timelines.

Official WhatsApp Group:
https://chat.whatsapp.com/Bvo5QC2xRrgA1TODMPx7L0?mode=gi_t
All participants must join the group for further updates and communication.

If you have any queries, please contact the organizing team.

Wishing you all the best for your hackathon journey!

Regards,
PRAKALP IoT Admin Team"""
        
        try:
            send_real_email(email, f"PRAKALP Assignment: {pid}", body)
            sent += 1
        except Exception as e:
            failed_list.append({'name': name, 'email': email, 'reason': str(e)[:50]})
    
    session['failed_emails'] = failed_list
    return redirect(url_for('admin') + f'?emailed=1&sent={sent}&failed={len(failed_list)}&step1_done=1&tab=setup')

@app.route('/finalize_registry', methods=['POST'])
def finalize_registry():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    csv_path = os.path.join('/tmp', 'latest_registry.csv')
    xlsx_path = os.path.join('/tmp', 'latest_registry.xlsx')
    target = csv_path if os.path.exists(csv_path) else (xlsx_path if os.path.exists(xlsx_path) else None)
    
    if not target: return redirect(url_for('admin') + '?error=no_registry_temp&tab=setup')
    initialize_db(target)
    return redirect(url_for('admin') + '?registered=1&tab=setup')

@app.route('/reset_db', methods=['POST'])
def reset_db():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    initialize_db()
    return redirect(url_for('admin') + '?reset=1&tab=setup')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)