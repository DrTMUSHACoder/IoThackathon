import os
import smtplib
import re
import pandas as pd
import sqlite3
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
SENDER_EMAIL = 'prakalp-hackathon@rcee.ac.in'
SENDER_PASSWORD = 'zlbrpnprgnynuzso'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# Create necessary directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🚀 Vercel fix: Use /tmp for writable files in serverless environment
if os.environ.get('VERCEL'):
    TMP_DIR = '/tmp'
else:
    TMP_DIR = os.path.join(BASE_DIR, 'data', 'tmp')
    os.makedirs(TMP_DIR, exist_ok=True)

REGISTRY_PATH = os.path.join(TMP_DIR, 'registry.csv')

def get_db_connection():
    url = os.environ.get('POSTGRES_URL') or os.environ.get('STORAGE_URL')
    if url:
        try:
            return psycopg2.connect(url, sslmode='require')
        except Exception as e:
            print(f"❌ Postgres error: {e}")
            return None
    else:
        # 📂 Fallback to local SQLite for development
        try:
            conn = sqlite3.connect(os.path.join(BASE_DIR, 'data', 'hackathon.db'))
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"❌ SQLite error: {e}")
            return None

# ==============================
# 📊 SCHEMA & METADATA
# ==============================
SCORING_FIELDS = {
    'R1': ['r1_innovation', 'r1_problemrelevance', 'r1_techfeasibility', 'r1_claritypresentation'],
    'R2': ['r2_feasibilityvalidation', 'r2_systemdesignlogic', 'r2_demoquality', 'r2_technicalunderstanding'],
    'R3P1': ['r3p1_initialimplementation', 'r3p1_approachmethodology', 'r3p1_progresslevel', 'r3p1_teamcoordination'],
    'R3P2': ['r3p2_improvementphase1', 'r3p2_innovationmodification', 'r3p2_problemsolvingapproach', 'r3p2_stabilityfunctionality'],
    'R4': ['r4_innovation', 'r4_workingprototype', 'r4_realtimeimpact', 'r4_presentationskills', 'r4_qahandling']
}

SCORING_META = {
    'R1': {'title': 'Round 1 – Idea Submission', 'desc': 'PPT pitch (3–5 min)', 'weight': '15%', 'criteria': [{'field': 'r1_innovation', 'label': 'Innovation', 'max': 15}, {'field': 'r1_problemrelevance', 'label': 'Problem Relevance', 'max': 10}, {'field': 'r1_techfeasibility', 'label': 'Technical Feasibility', 'max': 15}, {'field': 'r1_claritypresentation', 'label': 'Clarity of Presentation', 'max': 10}]},
    'R2': {'title': 'Round 2 – Concept Validation', 'desc': 'Simulation/Architecture', 'weight': '15%', 'criteria': [{'field': 'r2_feasibilityvalidation', 'label': 'Feasibility Validation', 'max': 20}, {'field': 'r2_systemdesignlogic', 'label': 'System Design & Logic', 'max': 15}, {'field': 'r2_demoquality', 'label': 'Demonstration Quality', 'max': 10}, {'field': 'r2_technicalunderstanding', 'label': 'Technical Understanding', 'max': 5}]},
    'R3P1': {'title': 'Round 3 – Phase 1', 'desc': 'Early Implementation', 'weight': '20%', 'criteria': [{'field': 'r3p1_initialimplementation', 'label': 'Initial Implementation', 'max': 20}, {'field': 'r3p1_approachmethodology', 'label': 'Approach & Methodology', 'max': 10}, {'field': 'r3p1_progresslevel', 'label': 'Progress Level', 'max': 10}, {'field': 'r3p1_teamcoordination', 'label': 'Team Coordination', 'max': 10}]},
    'R3P2': {'title': 'Round 3 – Phase 2', 'desc': 'Modification Phase', 'weight': '20%', 'criteria': [{'field': 'r3p2_improvementphase1', 'label': 'Improvement from Phase 1', 'max': 15}, {'field': 'r3p2_innovationmodification', 'label': 'Innovation in Modification', 'max': 15}, {'field': 'r3p2_problemsolvingapproach', 'label': 'Problem-Solving Approach', 'max': 10}, {'field': 'r3p2_stabilityfunctionality', 'label': 'Stability & Functionality', 'max': 10}]},
    'R4': {'title': 'Round 4 – Final Pitch', 'desc': 'Live Demo & Q&A', 'weight': '30%', 'criteria': [{'field': 'r4_innovation', 'label': 'Innovation', 'max': 10}, {'field': 'r4_workingprototype', 'label': 'Working Prototype', 'max': 15}, {'field': 'r4_realtimeimpact', 'label': 'Real-Time Impact', 'max': 10}, {'field': 'r4_presentationskills', 'label': 'Presentation Skills', 'max': 5}, {'field': 'r4_qahandling', 'label': 'Q&A Handling', 'max': 10}]}
}

def initialize_db(path=None):
    c = get_db_connection()
    if not c: return
    try:
        cur = c.cursor()
        schema = """CREATE TABLE IF NOT EXISTS teams (teamid TEXT PRIMARY KEY, projectid TEXT, teamname TEXT, projecttitle TEXT, email TEXT,
        r1_innovation NUMERIC DEFAULT 0, r1_problemrelevance NUMERIC DEFAULT 0, r1_techfeasibility NUMERIC DEFAULT 0, r1_claritypresentation NUMERIC DEFAULT 0,
        r2_feasibilityvalidation NUMERIC DEFAULT 0, r2_systemdesignlogic NUMERIC DEFAULT 0, r2_demoquality NUMERIC DEFAULT 0, r2_technicalunderstanding NUMERIC DEFAULT 0,
        r3p1_initialimplementation NUMERIC DEFAULT 0, r3p1_approachmethodology NUMERIC DEFAULT 0, r3p1_progresslevel NUMERIC DEFAULT 0, r3p1_teamcoordination NUMERIC DEFAULT 0,
        r3p2_improvementphase1 NUMERIC DEFAULT 0, r3p2_innovationmodification NUMERIC DEFAULT 0, r3p2_problemsolvingapproach NUMERIC DEFAULT 0, r3p2_stabilityfunctionality NUMERIC DEFAULT 0,
        r4_innovation NUMERIC DEFAULT 0, r4_workingprototype NUMERIC DEFAULT 0, r4_realtimeimpact NUMERIC DEFAULT 0, r4_presentationskills NUMERIC DEFAULT 0, r4_qahandling NUMERIC DEFAULT 0);"""
        cur.execute(schema)
        
        if path:
            print(f"📂 Initializing from: {path}")
            cur.execute("DELETE FROM teams;")
            c.commit() # 🔥 Immediate commit of the wipe
            
            df = pd.read_csv(path, sep=None, engine='python', encoding_errors='ignore') if str(path).lower().endswith('.csv') else pd.read_excel(path)
            df.columns = [str(col).strip() for col in df.columns]
            
            for r in df.to_dict(orient='records'):
                try:
                    def f(ks, exclude=None):
                        ks = [k.lower() for k in ks]
                        for rk in r.keys():
                            rk_clean = str(rk).lower().strip()
                            if exclude and any(ex.lower() in rk_clean for ex in exclude): continue
                            if any(k in rk_clean for k in ks): return str(r[rk]).strip()
                        return ""
                    
                    email = f(['Email', 'Mail', 'Id'], exclude=['@']) # exclude columns that aren't the email itself
                    if "@" not in email: # try harder finding it in any field
                        for val in r.values():
                            if isinstance(val, str) and "@" in val:
                                email = val.strip()
                                break
                    
                    if "@" in email:
                        tid = f(['Batch', 'TeamID', 'ProjectID']) or f(['No', 'ID']) or "0"
                        pid = f(['Batch', 'ProjectID', 'PID']) or "PR-IOT"
                        name = f(['Name', 'Student', 'Team']) or "Anonymous Team"
                        title = f(['Title', 'Problem', 'Statement']) or "Untitled Project"
                        
                        if isinstance(c, sqlite3.Connection):
                            cur.execute("INSERT OR REPLACE INTO teams (teamid, projectid, teamname, projecttitle, email) VALUES (?,?,?,?,?)", (tid, pid, name, title, email))
                        else:
                            cur.execute("INSERT INTO teams (teamid, projectid, teamname, projecttitle, email) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (teamid) DO UPDATE SET projectid=EXCLUDED.projectid, teamname=EXCLUDED.teamname, projecttitle=EXCLUDED.projecttitle, email=EXCLUDED.email;", (tid, pid, name, title, email))
                except Exception as row_err:
                    print(f"⚠️ Row error: {row_err}")
                    continue
            
            c.commit() # Final commit for inserts
            print("✅ Import finished.")
        else:
            c.commit() # Normal schema creation commit
    finally: c.close()

def get_teams():
    c = get_db_connection()
    if not c: return []
    try:
        if isinstance(c, sqlite3.Connection):
            raw = c.execute("SELECT * FROM teams;").fetchall()
            res = [dict(r) for r in raw]
        else:
            cur = c.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM teams;")
            res = [dict(r) for r in cur.fetchall()]
        
        for t in res:
            # Consistent mapping
            t['TeamID'], t['ProjectID'], t['TeamName'], t['ProjectTitle'], t['Email'] = t.get('teamid'), t.get('projectid'), t.get('teamname'), t.get('projecttitle'), t.get('email')
            for k in list(t.keys()):
                if k.startswith('r'): t[k] = float(t.get(k) or 0)
            
            def s(fs): return sum(float(t.get(f) or 0) for f in fs)
            t['R1_Total'], t['R2_Total'], t['R3P1_Total'], t['R3P2_Total'], t['R4_Total'] = s(SCORING_FIELDS['R1']), s(SCORING_FIELDS['R2']), s(SCORING_FIELDS['R3P1']), s(SCORING_FIELDS['R3P2']), s(SCORING_FIELDS['R4'])
            # 🏆 Final Combined Score
            t['Weighted_Total'] = (t['R1_Total']*0.3) + (t['R2_Total']*0.3) + (t['R3P1_Total']*0.4) + (t['R3P2_Total']*0.4) + (t['R4_Total']*0.6)
            t['Raw_Total'] = t['R1_Total'] + t['R2_Total'] + t['R3P1_Total'] + t['R3P2_Total'] + t['R4_Total']

        return sorted(res, key=lambda x: x.get('Weighted_Total', 0), reverse=True)
    except Exception as e:
        print(f"❌ Error in get_teams: {e}")
        initialize_db()
        return []
    finally: c.close()

# ==============================
# 📧 ENGINE & ROUTES
# ==============================
def send_email(to, sub, body):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = sub
        msg['From'] = f"PRAKALP 2026<{SENDER_EMAIL}>"
        msg['To'] = to.strip()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(SENDER_EMAIL, SENDER_PASSWORD)
            s.send_message(msg)
    except: pass

@app.route('/')
def index(): return render_template('index.html', teams=get_teams())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username')==ADMIN_USERNAME and request.form.get('password')==ADMIN_PASSWORD:
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
    fd, c = request.form.to_dict(), get_db_connection()
    if not c: return redirect(url_for('admin'))
    try:
        cur = c.cursor()
        for sno in set([k.split('_')[-1] for k in fd.keys() if '_' in k]):
            up, pa = [], []
            for fs in SCORING_FIELDS.values():
                for f in fs:
                    if f"{f}_{sno}" in fd:
                        up.append(f"{f} = %s" if not isinstance(c, sqlite3.Connection) else f"{f} = ?")
                        pa.append(float(fd[f"{f}_{sno}"] or 0))
            if up:
                pa.append(sno)
                query = f"UPDATE teams SET {', '.join(up)} WHERE teamid = %s" if not isinstance(c, sqlite3.Connection) else f"UPDATE teams SET {', '.join(up)} WHERE teamid = ?"
                cur.execute(query, pa)
        c.commit()
    finally: c.close()
    return redirect(url_for('admin') + '?saved=1')

@app.route('/upload_dispatch', methods=['POST'])
def upload_dispatch():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    file = request.files.get('registry_file')
    if not file: return redirect(url_for('admin'))
    file.save(REGISTRY_PATH)
    
    # 📧 Background Broadcast Simulation
    try:
        df = pd.read_csv(REGISTRY_PATH, sep=None, engine='python', encoding_errors='ignore') if REGISTRY_PATH.endswith('.csv') else pd.read_excel(REGISTRY_PATH)
        rows = df.to_dict(orient='records')
        sent = 0
        sent_emails = set()
        for r in rows:
            def f(ks):
                for k in ks:
                    for rk in r.keys():
                        if k.lower() in str(rk).lower(): return str(r[rk]).strip()
                return ""
            e = f(['Email', 'Mail']).lower()
            if "@" in e and e not in sent_emails:
                n, pid, title = f(['Name', 'Student', 'Team']), f(['Batch', 'Project', 'PID']), f(['Title', 'Problem', 'Statement'])
                body = f"""Dear Student, 

Greetings from PRAKALP Hackathon Team!

We are pleased to inform you that your problem statement has been officially assigned for the PRAKALP Hackathon.

Hackathon Project ID: {pid}
Problem Statement: {title}

You are requested to carefully go through the problem statement and start working on your project. Make sure to plan your approach, develop innovative solutions, and stay consistent with the given guidelines and timelines.

If you have any queries, please contact the organizing team.

Wishing you all the best for your Hackathon Journey!

Regards,
PRAKALP Admin Team"""
                send_email(e, f"PRAKALP Assignment: {pid}", body)
                sent_emails.add(e)
                sent += 1
        return redirect(url_for('admin') + f'?emailed=1&sent={sent}&step1_done=1&tab=setup')
    except Exception as e:
        print(f"❌ Dispatch error: {e}")
        return redirect(url_for('admin') + f'?error=dispatch_failed&tab=setup')

@app.route('/finalize_registry', methods=['POST'])
def finalize_registry():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    if os.path.exists(REGISTRY_PATH):
        initialize_db(REGISTRY_PATH)
    import time
    return redirect(url_for('admin') + f'?registered=1&tab=setup&t={int(time.time())}')

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
import io

# ... (Previous code remains the same)

@app.route('/download_results')
def download_results():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    teams = get_teams()
    if not teams: return "No data found."
    
    # 📊 Create Excel with Pandas
    df = pd.DataFrame(teams)
    
    # 🧹 Clean up for export
    cols = ['TeamID', 'ProjectID', 'TeamName', 'ProjectTitle', 'Email', 
            'R1_Total', 'R2_Total', 'R3P1_Total', 'R3P2_Total', 'R4_Total', 
            'Weighted_Total', 'Raw_Total']
    df = df[[c for c in cols if c in df.columns]]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Hackathon Results')
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name='iot_hackathon_final_results.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/reset_db', methods=['POST'])
def reset_db():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    initialize_db()
    return redirect(url_for('admin') + '?reset=1&tab=setup')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)