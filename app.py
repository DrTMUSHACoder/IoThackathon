import csv
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json

app = Flask(__name__)
app.secret_key = 'prakalp-secure-iot-key-2026'

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# 📂 Data Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'hackathon_detailed_scores.csv')
PROPOSAL_FILE = os.path.join(BASE_DIR, 'IoT_Hackathon_Proposals_Final.csv')

# 📊 Scoring Schema — Exact criteria from PRAKALP IoT Hackathon Plan of Action
SCORING_FIELDS = {
    'R1':   ['R1_Innovation', 'R1_ProblemRelevance', 'R1_TechFeasibility', 'R1_ClarityPresentation'],
    'R2':   ['R2_FeasibilityValidation', 'R2_SystemDesignLogic', 'R2_DemoQuality', 'R2_TechnicalUnderstanding'],
    'R3P1': ['R3P1_InitialImplementation', 'R3P1_ApproachMethodology', 'R3P1_ProgressLevel', 'R3P1_TeamCoordination'],
    'R3P2': ['R3P2_ImprovementPhase1', 'R3P2_InnovationModification', 'R3P2_ProblemSolvingApproach', 'R3P2_StabilityFunctionality'],
    'R4':   ['R4_Innovation', 'R4_WorkingPrototype', 'R4_RealTimeImpact', 'R4_PresentationSkills', 'R4_QAHandling']
}

# 🎯 Max marks per criterion — for UI validation and display
SCORING_META = {
    'R1': {
        'title': 'Round 1 – Idea Submission',
        'desc': '10:30 AM – 1:30 PM | PPT submission + 3–5 min pitch to judges',
        'weight': '15%',
        'criteria': [
            {'field': 'R1_Innovation',            'label': 'Innovation',              'max': 15},
            {'field': 'R1_ProblemRelevance',       'label': 'Problem Relevance',       'max': 10},
            {'field': 'R1_TechFeasibility',        'label': 'Technical Feasibility',   'max': 15},
            {'field': 'R1_ClarityPresentation',    'label': 'Clarity of Presentation', 'max': 10},
        ]
    },
    'R2': {
        'title': 'Round 2 – Simulation / Concept Validation',
        'desc': '2:15 PM – 5:30 PM | Simulation or architecture demonstration',
        'weight': '15%',
        'criteria': [
            {'field': 'R2_FeasibilityValidation',     'label': 'Feasibility Validation',    'max': 20},
            {'field': 'R2_SystemDesignLogic',         'label': 'System Design & Logic',     'max': 15},
            {'field': 'R2_DemoQuality',               'label': 'Demonstration Quality',     'max': 10},
            {'field': 'R2_TechnicalUnderstanding',    'label': 'Technical Understanding',   'max':  5},
        ]
    },
    'R3P1': {
        'title': 'Round 3 – Iterative Development (Phase 1)',
        'desc': '6:00 PM – 8:30 PM | Prototype development begins',
        'weight': '20%',
        'criteria': [
            {'field': 'R3P1_InitialImplementation',  'label': 'Initial Implementation',   'max': 20},
            {'field': 'R3P1_ApproachMethodology',    'label': 'Approach & Methodology',   'max': 10},
            {'field': 'R3P1_ProgressLevel',          'label': 'Progress Level',           'max': 10},
            {'field': 'R3P1_TeamCoordination',       'label': 'Team Coordination',        'max': 10},
        ]
    },
    'R3P2': {
        'title': 'Round 3 – Iterative Development (Phase 2)',
        'desc': '10:30 PM – 1:30 AM | Implementation of Modification 2',
        'weight': '20%',
        'criteria': [
            {'field': 'R3P2_ImprovementPhase1',         'label': 'Improvement from Phase 1',    'max': 15},
            {'field': 'R3P2_InnovationModification',    'label': 'Innovation in Modification',  'max': 15},
            {'field': 'R3P2_ProblemSolvingApproach',    'label': 'Problem-Solving Approach',    'max': 10},
            {'field': 'R3P2_StabilityFunctionality',    'label': 'Stability & Functionality',   'max': 10},
        ]
    },
    'R4': {
        'title': 'Round 4 – Final Pitch & Demonstration',
        'desc': '8:00 AM – 10:00 AM | Presentation, live demo & Q&A',
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

def initialize_db(registry_path=None):
    """Seed the database from a registry CSV or fallback to Proposal Matrix."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    
    data = []
    
    if registry_path and os.path.exists(registry_path):
        with open(registry_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team_row = {
                    'TeamID': row.get('TeamID', row.get('S.No', '')),
                    'ProjectID': row.get('ProjectID', ''),
                    'TeamName': row.get('TeamName', ''),
                    'ProjectTitle': row.get('ProjectTitle', ''),
                    'Email': row.get('LeaderEmail', row.get('Email', ''))
                }
                for field in HEADERS[5:]:
                    team_row[field] = 0
                data.append(team_row)
    else:
        # Organic Fallback to original 45 Teams if no explicit upload triggered
        with open(PROPOSAL_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sno = row.get('S.No', '')
                team_row = {
                    'TeamID': sno,
                    'ProjectID': f"PID-{str(sno).zfill(2)}",
                    'TeamName': f"Team {str(sno).zfill(2)}" if sno else "Unknown Team",
                    'ProjectTitle': row.get('Project Title', ''),
                    'Email': 'placeholder@example.com'
                }
                for field in HEADERS[5:]:
                    team_row[field] = 0
                data.append(team_row)

    with open(DATA_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(data)

def get_teams():
    """Fetch teams from CSV and calculate live totals/ranks."""
    teams = []
    if not os.path.exists(DATA_FILE): initialize_db()
    
    with open(DATA_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Helper to safely sum fields
            def sum_round(fields):
                return sum(float(row.get(f, 0)) for f in fields)
            
            row['R1_Total'] = sum_round(SCORING_FIELDS['R1'])
            row['R2_Total'] = sum_round(SCORING_FIELDS['R2'])
            row['R3P1_Total'] = sum_round(SCORING_FIELDS['R3P1'])
            row['R3P2_Total'] = sum_round(SCORING_FIELDS['R3P2'])
            row['R4_Total'] = sum_round(SCORING_FIELDS['R4'])
            
            # Weighted Calculation based on Document
            # R1: 15% (0.3 of 50), R2: 15% (0.3), R3P1: 20% (0.4), R3P2: 20% (0.4), R4: 30% (0.6)
            row['Weighted_Total'] = (row['R1_Total'] * 0.3) + \
                                    (row['R2_Total'] * 0.3) + \
                                    (row['R3P1_Total'] * 0.4) + \
                                    (row['R3P2_Total'] * 0.4) + \
                                    (row['R4_Total'] * 0.6)
            
            row['Raw_Total'] = row['R1_Total'] + row['R2_Total'] + \
                               row['R3P1_Total'] + row['R3P2_Total'] + row['R4_Total']
            
            teams.append(row)
    
    # Sort by weighted total descending
    return sorted(teams, key=lambda x: float(x['Weighted_Total']), reverse=True)

@app.route('/')
def index():
    """Main Leaderboard View with Aesthetic styling."""
    teams = get_teams()
    return render_template('index.html', teams=teams)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Secure Admin Portal Entry."""
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Invalid credentials. Please attempt again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """End Admin Session."""
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    """Admin Bulk-Entry Portal."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    teams = get_teams()
    return render_template('admin.html', teams=teams, fields=SCORING_FIELDS, meta=SCORING_META)

@app.route('/update_scores', methods=['POST'])
def update_scores():
    """API endpoint to save all detailed scores from the admin panel."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    form_data = request.form.to_dict()
    current_teams = get_teams()
    updated_teams = []
    
    for team in current_teams:
        sno = team['TeamID']
        for round_name, sub_fields in SCORING_FIELDS.items():
            for field in sub_fields:
                key = f"{field}_{sno}"
                if key in form_data:
                    team[field] = form_data[key]
        updated_teams.append(team)

    with open(DATA_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(updated_teams)
        
    return redirect(url_for('admin') + '?saved=1')

@app.route('/upload_registry', methods=['POST'])
def upload_registry():
    """Admin initializes the DB from an uploaded CSV."""
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    
    file = request.files.get('registry_file')
    if file and file.filename.endswith('.csv'):
        temp_path = os.path.join(BASE_DIR, 'data', 'temp_registry.csv')
        file.save(temp_path)
        initialize_db(temp_path)
        os.remove(temp_path)
        return redirect(url_for('admin') + '?registered=1')
    return redirect(url_for('admin') + '?error=invalid_file')

@app.route('/send_startup_emails', methods=['POST'])
def send_startup_emails():
    """Mock sending project IDs to teams."""
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    
    teams = get_teams()
    for t in teams:
        print(f"📧 [EMAIL DISPATCH] To: {t['Email']} | Welcome {t['TeamName']}! Your assigned Project ID is: {t['ProjectID']} for '{t['ProjectTitle']}'. Best of luck!")
        
    return redirect(url_for('admin') + '?emailed=1')

@app.route('/send_emails', methods=['POST'])
def send_emails():
    """Logic for bulk dispatching personalized emails."""
    teams = get_teams()
    sent_count = 0
    for team in teams:
        if team['Email'] != 'placeholder@example.com':
            # Async Logic (Mocked)
            print(f"Sending Mock Email to {team['Email']}")
            sent_count += 1
            
    return jsonify({"status": "success", "count": sent_count})

@app.route('/announce_prize', methods=['POST'])
def announce_prize():
    """Admin triggers Prize Announcement."""
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    
    team_id = request.form.get('team_id')
    rank = int(request.form.get('rank', 0))
    teams = get_teams()
    
    # Identify prize based on new rules
    if rank == 1: prize = "1st Prize 🥇"
    elif rank == 2: prize = "2nd Prize 🥈"
    elif 3 <= rank <= 5: prize = "3rd Prize 🥉"
    else: return redirect(url_for('index'))
    
    # Find active team
    target_team = next((t for t in teams if str(t['TeamID']) == str(team_id)), None)
    if target_team:
        print(f"==================================================")
        print(f"📧 [PRIZE DISPATCH] To: {target_team.get('Email', 'Unknown')}")
        print(f"Dear {target_team.get('TeamName', 'Team')},")
        print(f"Congratulations! We are thrilled to announce that your incredible project '{target_team.get('ProjectTitle', 'Project')}' (Project ID: {target_team.get('ProjectID', 'Unknown')}) has officially secured {prize} in the PRAKALP IoT Hackathon!")
        print(f"==================================================")
        
    return redirect(url_for('index') + f'?announced={team_id}')

if __name__ == '__main__':
    initialize_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
