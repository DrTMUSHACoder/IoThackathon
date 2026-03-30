import csv
import os
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
import pandas as pd

app = Flask(__name__)
app.secret_key = 'prakalp-secure-iot-key-2026'

# ==============================
# 🔐 EMAIL CONFIG (UPDATE THIS)
# ==============================
SENDER_EMAIL = 'ushawin2020@gmail.com'
SENDER_PASSWORD = 'pvpknwqgsuttuqlm' # 💡 Restore your working password here

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# ==============================
# 📂 FILE PATHS
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'hackathon_detailed_scores.csv')
PROPOSAL_FILE = os.path.join(BASE_DIR, 'IoT_Hackathon_Proposals_Final.csv')

# ==============================
# 📊 SCHEMA & METADATA
# ==============================
SCORING_FIELDS = {
    'R1':   ['R1_Innovation', 'R1_ProblemRelevance', 'R1_TechFeasibility', 'R1_ClarityPresentation'],
    'R2':   ['R2_FeasibilityValidation', 'R2_SystemDesignLogic', 'R2_DemoQuality', 'R2_TechnicalUnderstanding'],
    'R3P1': ['R3P1_InitialImplementation', 'R3P1_ApproachMethodology', 'R3P1_ProgressLevel', 'R3P1_TeamCoordination'],
    'R3P2': ['R3P2_ImprovementPhase1', 'R3P2_InnovationModification', 'R3P2_ProblemSolvingApproach', 'R3P2_StabilityFunctionality'],
    'R4':   ['R4_Innovation', 'R4_WorkingPrototype', 'R4_RealTimeImpact', 'R4_PresentationSkills', 'R4_QAHandling']
}

SCORING_META = {
    'R1': {
        'title': 'Round 1 – Idea Submission',
        'desc': 'PPT submission + 3–5 min pitch to judges',
        'weight': '15%',
        'criteria': [
            {'field': 'R1_Innovation',            'label': 'Innovation',              'max': 15},
            {'field': 'R1_ProblemRelevance',       'label': 'Problem Relevance',       'max': 10},
            {'field': 'R1_TechFeasibility',        'label': 'Technical Feasibility',   'max': 15},
            {'field': 'R1_ClarityPresentation',    'label': 'Clarity of Presentation', 'max': 10},
        ]
    },
    'R2': {
        'title': 'Round 2 – Concept Validation',
        'desc': 'Simulation or architecture demonstration',
        'weight': '15%',
        'criteria': [
            {'field': 'R2_FeasibilityValidation',     'label': 'Feasibility Validation',    'max': 20},
            {'field': 'R2_SystemDesignLogic',         'label': 'System Design & Logic',     'max': 15},
            {'field': 'R2_DemoQuality',               'label': 'Demonstration Quality',     'max': 10},
            {'field': 'R2_TechnicalUnderstanding',    'label': 'Technical Understanding',   'max':  5},
        ]
    },
    'R3P1': {
        'title': 'Round 3 – Phase 1',
        'desc': 'Prototype development begins',
        'weight': '20%',
        'criteria': [
            {'field': 'R3P1_InitialImplementation',  'label': 'Initial Implementation',   'max': 20},
            {'field': 'R3P1_ApproachMethodology',    'label': 'Approach & Methodology',   'max': 10},
            {'field': 'R3P1_ProgressLevel',          'label': 'Progress Level',           'max': 10},
            {'field': 'R3P1_TeamCoordination',       'label': 'Team Coordination',        'max': 10},
        ]
    },
    'R3P2': {
        'title': 'Round 3 – Phase 2',
        'desc': 'Implementation of Modification 2',
        'weight': '20%',
        'criteria': [
            {'field': 'R3P2_ImprovementPhase1',         'label': 'Improvement from Phase 1',    'max': 15},
            {'field': 'R3P2_InnovationModification',    'label': 'Innovation in Modification',  'max': 15},
            {'field': 'R3P2_ProblemSolvingApproach',    'label': 'Problem-Solving Approach',    'max': 10},
            {'field': 'R3P2_StabilityFunctionality',    'label': 'Stability & Functionality',   'max': 10},
        ]
    },
    'R4': {
        'title': 'Round 4 – Final Pitch',
        'desc': 'Presentation, live demo & Q&A',
        'weight': '30%',
        'criteria': [
            {'field': 'R4_Innovation',          'label': 'Innovation',                    'max': 10},
            {'field': 'R4_WorkingPrototype',    'label': 'Working Prototype',             'max': 15},
            {'field': 'R4_RealTimeImpact',      'label': 'Real-Time Application Impact',  'max': 10},
            {'field': 'R4_PresentationSkills',  'label': 'Presentation Skills',           'max':  5},
            {'field': 'R4_QAHandling',          'label': 'Q&A Handling',                  'max': 10},
        ]
    }
}

HEADERS = ['TeamID', 'ProjectID', 'TeamName', 'ProjectTitle', 'Email']
for fields in SCORING_FIELDS.values():
    HEADERS.extend(fields)
HEADERS.extend(['R1_Total', 'R2_Total', 'R3P1_Total', 'R3P2_Total', 'R4_Total', 'Weighted_Total', 'Raw_Total'])

# ==============================
# 📥 DB INITIALIZATION
# ==============================
def initialize_db(registry_path=None):
    """Seed the database from a registry CSV or fallback to Proposal Matrix."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    data = []
    
    if registry_path and os.path.exists(registry_path):
        if registry_path.endswith('.csv'):
            df = pd.read_csv(registry_path, sep=None, engine='python', encoding_errors='ignore')
        else:
            df = pd.read_excel(registry_path)
        
        # 🧹 AGGRESSIVE HEADER CLEANING
        df.columns = [str(c).strip() for c in df.columns]
        rows = df.to_dict(orient='records')

        print(f"[DB] SCANNING REGISTRY: Found {len(rows)} rows. Headers detected: {list(df.columns)}")
        
        for row in rows:
            # 🕵️ FUZZY MAPPING
            def find_val(keys):
                for k in keys:
                    for rk in row.keys():
                        clean_rk = str(rk).lower().strip().replace("_", "").replace(" ", "")
                        clean_k = str(k).lower().strip().replace("_", "").replace(" ", "")
                        if clean_k == clean_rk: return row[rk]
                return ""

            email = str(find_val(['Email', 'MailId', 'EmailID', 'Mail Id', 'LeaderEmail'])).strip()
            
            # Skip invalid
            if not email or "@" not in email or "placeholder" in email:
                continue

            team_row = {
                'TeamID': find_val(['SNo', 'TeamID', 'ID', 'S.No']),
                'ProjectID': find_val(['BatchNO', 'ProjectID', 'PID', 'Batch NO']),
                'TeamName': find_val(['NameoftheStudent', 'TeamName', 'StudentName', 'Name', 'Name of The Student']),
                'ProjectTitle': find_val(['ProblemStatement', 'ProjectTitle', 'Title', 'ProblemStatement', 'Problem Statement']),
                'Email': email
            }
            # Initialize scoring fields
            for field in HEADERS[5:]: team_row[field] = 0
            data.append(team_row)
            
        print(f"[DB] SUCCESS: Logged {len(data)} valid teams into the system.")
    else:
        if os.path.exists(PROPOSAL_FILE):
            with open(PROPOSAL_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sno = row.get('S.No', '')
                    team_row = {
                        'TeamID': sno,
                        'ProjectID': f"PID-{str(sno).zfill(2)}",
                        'TeamName': f"Team {str(sno).zfill(2)}" if sno else "Unknown Team",
                        'ProjectTitle': row.get('Project Title', ''),
                        'Email': 'placeholder@example.com' # 🛑 SAFETY FILTER WILL SKIP THIS
                    }
                    for field in HEADERS[5:]: team_row[field] = 0
                    data.append(team_row)

    with open(DATA_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(data)

def get_teams():
    if not os.path.exists(DATA_FILE): initialize_db()
    teams = []
    with open(DATA_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            def sum_round(fields): return sum(float(row.get(f, 0)) for f in fields)
            row['R1_Total'] = sum_round(SCORING_FIELDS['R1'])
            row['R2_Total'] = sum_round(SCORING_FIELDS['R2'])
            row['R3P1_Total'] = sum_round(SCORING_FIELDS['R3P1'])
            row['R3P2_Total'] = sum_round(SCORING_FIELDS['R3P2'])
            row['R4_Total'] = sum_round(SCORING_FIELDS['R4'])
            row['Weighted_Total'] = (row['R1_Total'] * 0.3) + (row['R2_Total'] * 0.3) + (row['R3P1_Total'] * 0.4) + (row['R3P2_Total'] * 0.4) + (row['R4_Total'] * 0.6)
            row['Raw_Total'] = row['R1_Total'] + row['R2_Total'] + row['R3P1_Total'] + row['R3P2_Total'] + row['R4_Total']
            teams.append(row)
    return sorted(teams, key=lambda x: float(x['Weighted_Total']), reverse=True)

# ==============================
# 📧 EMAIL ENGINE
# ==============================
def send_real_email(to_email, subject, body):
    # 🛡️ SAFETY CHECK: SKIP PLACEHOLDERS & INVALID EMAILS
    clean_addr = to_email.strip().replace(" ", "")
    if not clean_addr or "placeholder@example.com" in clean_addr or "@" not in clean_addr:
        print(f"[SKIPPED] System blocked delivery to invalid/placeholder address: {clean_addr}")
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = f"PRAKALP 2026 <{SENDER_EMAIL}>"
        msg['To'] = clean_addr
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"[SUCCESS] Email delivered to: {clean_addr}")
    except Exception as e:
        print(f"[ERROR] SMTP Failed to {clean_addr}: {e}")

# ==============================
# 🌐 ROUTES
# ==============================
@app.route('/')
def index():
    return render_template('index.html', teams=get_teams())

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else: error = 'Invalid credentials.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    return render_template('admin.html', teams=get_teams(), fields=SCORING_FIELDS, meta=SCORING_META)

@app.route('/update_scores', methods=['POST'])
def update_scores():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    form_data = request.form.to_dict()
    current_teams = get_teams()
    for team in current_teams:
        sno = team['TeamID']
        for round_name, sub_fields in SCORING_FIELDS.items():
            for field in sub_fields:
                key = f"{field}_{sno}"
                if key in form_data: team[field] = form_data[key]
    with open(DATA_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(current_teams)
    return redirect(url_for('admin') + '?saved=1')

@app.route('/upload_registry', methods=['POST'])
def upload_registry():
    """Admin initializes the DB from an uploaded CSV or XLSX."""
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    
    file = request.files.get('registry_file')
    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        ext = '.csv' if file.filename.endswith('.csv') else '.xlsx'
        temp_path = os.path.join(BASE_DIR, 'data', f'temp_registry{ext}')
        file.save(temp_path)
        initialize_db(temp_path)
        os.remove(temp_path)
        return redirect(url_for('admin') + '?registered=1')
    return redirect(url_for('admin') + '?error=invalid_file')

@app.route('/send_startup_emails', methods=['POST'])
def send_startup_emails():
    """Iterate through all registered teams and dispatch official hackathon credentials."""
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    
    current_teams = get_teams()
    sent_count, skip_count = 0, 0
    
    for t in current_teams:
        email = t.get('Email', '').strip()
        
        # 🛡️ Safety Filter (Shared logic with send_real_email)
        if not email or "placeholder" in email or "@" not in email:
            skip_count += 1
            continue

        body = f"""Dear Student ({t.get('TeamName')}),

Greetings from PRAKALP IoT Hackathon Team!

We are pleased to inform you that your problem statement has been officially assigned for the PRAKALP IoT Hackathon.

Hackathon Project ID: {t.get('ProjectID')}
Problem Statement: "{t.get('ProjectTitle')}"

You are requested to carefully go through the problem statement and start working on your project. Make sure to plan your approach, develop innovative solutions, and stay consistent with the given guidelines and timelines.

Official WhatsApp Group:
https://chat.whatsapp.com/Bvo5QC2xRrgA1TODMPx7L0?mode=gi_t
All participants must join the group for further updates and communication.

If you have any queries, please contact the organizing team.

Wishing you all the best for your hackathon journey!

Regards,
PRAKALP IoT Admin Team"""
        try:
            send_real_email(email, f"PRAKALP IoT Hackathon: Project Assignment ({t.get('ProjectID')})", body)
            sent_count += 1
        except: skip_count += 1
    
    return redirect(url_for('admin') + f'?emailed=1&sent={sent_count}&skipped={skip_count}')

@app.route('/announce_prize', methods=['POST'])
def announce_prize():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    team_id, rank = request.form.get('team_id'), int(request.form.get('rank', 0))
    if rank == 1: prize, subject = "1st Prize", "You won 1st Prize in PRAKALP 2026!"
    elif rank == 2: prize, subject = "2nd Prize", "You won 2nd Prize in PRAKALP 2026!"
    elif 3 <= rank <= 5: prize, subject = "3rd Prize", "You won 3rd Prize in PRAKALP 2026!"
    else: return redirect(url_for('index'))
    team = next((t for t in get_teams() if str(t['TeamID']) == str(team_id)), None)
    if team:
        body = f"Dear {team.get('TeamName')},\n\nCongratulations! We are thrilled to announce that your incredible project '{team.get('ProjectTitle')}' (Project ID: {team.get('ProjectID')}) has officially secured {prize} in the IoT Hackathon!\n\nPlease head to the main stage.\n\n- Hackathon Admin"
        send_real_email(team.get('Email', ''), subject, body)
    return redirect(url_for('index') + f'?announced={team_id}')

@app.route('/test_email', methods=['GET', 'POST'])
def test_email():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    result, t1, t2, t3 = None, "drtmusha@rcee.ac.in", "", ""
    if request.method == 'POST':
        targets = [t for t in [request.form.get('target_email_1'), request.form.get('target_email_2'), request.form.get('target_email_3')] if t]
        if not targets:
            result = "[ERROR] PLEASE ENTER AT LEAST 1 EMAIL!"
        else:
            body = """Dear Student,

Greetings from PRAKALP IoT Hackathon Team!

We are pleased to inform you that your problem statement has been officially assigned for the PRAKALP IoT Hackathon.

Hackathon Project ID: PR-IOT-1A-001
Problem Statement: "Automated Smart Home Bathroom Aerated Occupancy Sensing System using Arduino"

You are requested to carefully go through the problem statement and start working on your project. Make sure to plan your approach, develop innovative solutions, and stay consistent with the given guidelines and timelines.

Official WhatsApp Group:
https://chat.whatsapp.com/Bvo5QC2xRrgA1TODMPx7L0?mode=gi_t
All participants must join the group for further updates and communication.

If you have any queries, please contact the organizing team.

Wishing you all the best for your hackathon journey!

Regards,
PRAKALP IoT Admin Team"""
            try:
                for target in targets:
                    send_real_email(target, "PRAKALP IoT Hackathon: Project Assignment", body)
                result = f"[SUCCESS] Delivered to {len(targets)} inboxes!"
            except Exception as e: result = f"[ERROR] {str(e)}"
    return render_template('test_email.html', sender=SENDER_EMAIL, target_1=t1, target_2=t2, target_3=t3, result=result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)