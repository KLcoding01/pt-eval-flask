import os
import io
import re
import json
from flask import (Flask, request, jsonify, redirect, url_for, flash, render_template, send_file, session)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from dotenv import load_dotenv
from openai import OpenAI
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import date, datetime, timedelta
from io import BytesIO
from functools import wraps
from flask_sqlalchemy import SQLAlchemy

# Google Calendar imports
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# DB MODELS
from models import db, CPTCode, ICD10Code, Patient, Visit, Attachment, Billing, Visit, Therapist, Physician, Insurance, PTNote

# CONFIG & INIT
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_me")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db.init_app(app)
with app.app_context():
    db.create_all()

# OPENAI
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
MODEL = "gpt-4o-mini"

# AUTH
USERS = {"kelvin": "Thanh123!", "test1": "test1"}
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS and USERS[username] == password:
            session['username'] = username
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password."
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    session.pop('credentials', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

# =================== GOOGLE CALENDAR INTEGRATION ===================
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    creds_data = session.get('credentials')
    if not creds_data:
        return None
    creds = Credentials(**creds_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session['credentials'] = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
    service = build('calendar', 'v3', credentials=creds)
    return service

def create_google_event(visit):
    service = get_google_calendar_service()
    if not service:
        return None
    event_body = {
        'summary': f"{visit.patient.first_name} {visit.patient.last_name} - {visit.visit_type}",
        'start': {'dateTime': visit.visit_date.isoformat(), 'timeZone': 'America/Los_Angeles'},
        'end': {'dateTime': (visit.visit_date + timedelta(minutes=getattr(visit, "duration", 60))).isoformat(), 'timeZone': 'America/Los_Angeles'},
        'description': f"Therapist ID: {visit.therapist_id}"
    }
    event = service.events().insert(calendarId='primary', body=event_body).execute()
    return event.get('id')

def update_google_event(visit):
    service = get_google_calendar_service()
    if not service or not visit.google_event_id:
        return False
    event_body = {
        'summary': f"{visit.patient.first_name} {visit.patient.last_name} - {visit.visit_type}",
        'start': {'dateTime': visit.visit_date.isoformat(), 'timeZone': 'America/Los_Angeles'},
        'end': {'dateTime': (visit.visit_date + timedelta(minutes=getattr(visit, "duration", 60))).isoformat(), 'timeZone': 'America/Los_Angeles'},
        'description': f"Therapist ID: {visit.therapist_id}"
    }
    service.events().update(calendarId='primary', eventId=visit.google_event_id, body=event_body).execute()
    return True

def delete_google_event(visit):
    service = get_google_calendar_service()
    if not service or not visit.google_event_id:
        return False
    try:
        service.events().delete(calendarId='primary', eventId=visit.google_event_id).execute()
        return True
    except Exception as e:
        print(f"Google Calendar delete event error: {e}")
        return False

@app.route('/authorize')
@login_required
def authorize():
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
@login_required
def oauth2callback():
    state = session.get('state')
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    flash("Google Calendar connected!", "success")
    return redirect(url_for('dashboard'))

@app.route('/api/events')
@login_required
def api_events():
    service = get_google_calendar_service()
    if not service:
        return jsonify([])
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        items = events_result.get('items', [])
        events = []
        for item in items:
            start = item['start'].get('dateTime', item['start'].get('date'))
            end = item['end'].get('dateTime', item['end'].get('date'))
            events.append({
                'id': item['id'],
                'title': item.get('summary', 'No Title'),
                'start': start,
                'end': end,
            })
        return jsonify(events)
    except Exception as e:
        return jsonify([{"title": "Error loading events", "start": datetime.utcnow().isoformat()}])
        
@app.route('/api/patient_list')
def api_patient_list():
    patients = Patient.query.order_by(Patient.last_name).all()
    return jsonify([
        {
            "id": p.id,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "dob": p.dob.strftime('%Y-%m-%d') if p.dob else ""
        }
        for p in patients
    ])
    
@app.route('/pt_save_to_patient', methods=['POST'])
@login_required
def pt_save_to_patient():
    data = request.get_json()
    patient_id = data.get('patient_id')
    # For now, use None as therapist_id (SAFE DEFAULT)
    therapist_id = None
    # If your session has a therapist, you can use it. For now, just None.

    # Save all eval info as a text blob in the Visit notes field (JSON for full info)
    notes_json = json.dumps(data, indent=2)

    # Create Visit
    visit = Visit(
        patient_id=patient_id,
        therapist_id=therapist_id,
        visit_type='PT Evaluation',
        status='Completed',
        visit_date=datetime.now(),
        notes=notes_json
    )
    db.session.add(visit)
    db.session.commit()

    # Save PTNote (for quick display; can be the summary or whole notes)
    pt_note = PTNote(
        patient_id=patient_id,
        visit_id=visit.id,
        content=data.get('summary') or notes_json,  # Save the AI summary, or fallback to full data
        date_created=datetime.now()
    )
    db.session.add(pt_note)
    db.session.commit()

    return jsonify({"message": "PT Evaluation saved to patient as Visit and Note."})
    
    
@app.route('/edit_visit_date/<int:visit_id>', methods=['POST'])
def edit_visit_date(visit_id):
    new_date = request.form.get('date')
    visit = Visit.query.get_or_404(visit_id)
    visit.date = new_date
    db.session.commit()
    return redirect(url_for('patient_profile', patient_id=visit.patient_id))

@app.route('/visit/<int:visit_id>')
@login_required
def view_visit(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    eval_data = None
    try:
        import json
        eval_data = json.loads(visit.notes) if visit.notes else None
    except Exception:
        eval_data = visit.notes
    return render_template('visit_detail.html', visit=visit, eval_data=eval_data)

@app.route("/visits")
@login_required
def visit_list():
    visits = Visit.query.order_by(Visit.visit_date.desc()).all()
    notes = PTNote.query.order_by(PTNote.date_created.desc()).all() 
    return render_template("visit_list.html", visits=visits, notes=notes)

@app.route("/visit/<int:visit_id>")
@login_required
def view_visit_note(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    return render_template("view_visit_note.html", visit=visit)

@app.route("/patient/<int:patient_id>/notes")
@login_required
def patient_notes(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    # Corrected this line to use date_created instead of created_at
    notes = PTNote.query.filter_by(patient_id=patient_id).order_by(PTNote.date_created.desc()).all()
    visits = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.visit_date.desc()).all()
    return render_template("patient_notes.html", patient=patient, notes=notes, visits=visits)

    
@app.route('/add_visit', methods=['GET', 'POST'])
@login_required
def add_visit():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        therapist_id = request.form.get('therapist_id')
        visit_date_str = request.form.get('visit_date')
        end_time_str = request.form.get('end_time')
        duration = request.form.get('duration')
        visit_type = request.form.get('visit_type')
        status = request.form.get('status')
        cpt_code_id = request.form.get('cpt_code_id')
        icd10_code_id = request.form.get('icd10_code_id')
        notes = request.form.get('notes')
        google_event_id = request.form.get('google_event_id')

        # ---- FIX 1: Parse datetime ----
        visit_date = datetime.strptime(visit_date_str, "%Y-%m-%dT%H:%M") if visit_date_str else None
        end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M") if end_time_str else None

        # ---- FIX 2: Validate patient_id ----
        if not patient_id:
            flash("Patient is required!", "danger")
            return redirect(request.url)
        
        # You may want to validate therapist_id and others too.

        visit = Visit(
            patient_id=patient_id,
            therapist_id=therapist_id,
            visit_date=visit_date,
            end_time=end_time,
            duration=duration,
            visit_type=visit_type,
            status=status,
            cpt_code_id=cpt_code_id if cpt_code_id else None,
            icd10_code_id=icd10_code_id if icd10_code_id else None,
            notes=notes,
            google_event_id=google_event_id
        )
        db.session.add(visit)
        db.session.commit()
        flash("Visit added!", "success")
        return redirect(url_for('visit_list'))

    # GET: show form
    patients = Patient.query.all()
    therapists = Therapist.query.all()
    cpt_codes = CPTCode.query.all()
    icd10_codes = ICD10Code.query.all()
    return render_template(
        'visit_form.html',
        patients=patients,
        therapists=therapists,
        cpt_codes=cpt_codes,
        icd10_codes=icd10_codes
    )
    
# ========== DASHBOARD ==========
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# ========== PATIENT CRUD ==========

@app.route('/patients')
@login_required
def patients_list():
    patients = Patient.query.all()
    return render_template('patients.html', patients=patients, active_page='pt_builder')

@app.route('/patients/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    visits = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.visit_date.desc()).all()
    attachments = Attachment.query.filter_by(patient_id=patient_id).order_by(Attachment.uploaded_at.desc()).all()
    return render_template('patient_detail.html', patient=patient, visits=visits, attachments=attachments)


@app.route('/patients/new', methods=['GET', 'POST'])
@login_required
def new_patient():
    insurances = Insurance.query.all()
    physicians = Physician.query.all()
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        dob = request.form.get('dob') or None
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        insurance_id = request.form.get('insurance_id') or None
        physician_id = request.form.get('physician_id') or None

        # Convert dob to date if provided
        dob_date = datetime.strptime(dob, "%Y-%m-%d").date() if dob else None

        if not first_name or not last_name:
            flash("First name and last name are required.", "danger")
            return redirect(url_for('new_patient'))

        patient = Patient(
            first_name=first_name,
            last_name=last_name,
            dob=dob_date,
            phone=phone,
            email=email,
            address=address,
            insurance_id=insurance_id if insurance_id else None,
            physician_id=physician_id if physician_id else None
        )
        db.session.add(patient)
        db.session.commit()
        flash("New patient added!", "success")
        return redirect(url_for('patients_list'))
    return render_template('patient_form.html', patient=None, insurances=insurances, physicians=physicians)
    
# 3. Edit patient
@app.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    insurances = Insurance.query.all()
    physicians = Physician.query.all()
    if request.method == 'POST':
        patient.first_name = request.form.get('first_name')
        patient.last_name = request.form.get('last_name')
        dob = request.form.get('dob') or None
        patient.dob = datetime.strptime(dob, "%Y-%m-%d").date() if dob else None
        patient.phone = request.form.get('phone')
        patient.email = request.form.get('email')
        patient.address = request.form.get('address')
        insurance_id = request.form.get('insurance_id') or None
        physician_id = request.form.get('physician_id') or None
        patient.insurance_id = insurance_id if insurance_id else None
        patient.physician_id = physician_id if physician_id else None

        db.session.commit()
        flash("Patient updated!", "success")
        return redirect(url_for('patients_list'))
    return render_template('patient_form.html', patient=patient, insurances=insurances, physicians=physicians)

# ========== VISIT CRUD WITH GOOGLE CALENDAR SYNC ==========
@app.route('/visits')
@login_required
def visits_list():
    visits = Visit.query.order_by(Visit.visit_date.desc()).all()
    return render_template('visits_list.html', visits=visits)

@app.route('/visits/<int:visit_id>')
@login_required
def visit_detail(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    pt_note = PTNote.query.filter_by(visit_id=visit.id).order_by(PTNote.date_created.desc()).first()
    return render_template('visit_detail.html', visit=visit, pt_note=pt_note)

@app.route('/visits/new', methods=['GET', 'POST'])
@login_required
def new_visit():
    patients = Patient.query.all()
    therapists = Therapist.query.all()
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        therapist_id = request.form.get('therapist_id')
        visit_type = request.form.get('visit_type')
        visit_date = request.form.get('visit_date')
        visit_time = request.form.get('visit_time')
        status = request.form.get('status', 'Scheduled')
        dt_start = datetime.strptime(f"{visit_date} {visit_time}", "%m-%d-%Y %H:%M")
        duration = 60
        visit = Visit(
            patient_id=patient_id,
            therapist_id=therapist_id,
            visit_type=visit_type,
            visit_date=dt_start,
            duration=duration,
            status=status
        )
        db.session.add(visit)
        db.session.commit()
        # Google Calendar sync
        event_id = create_google_event(visit)
        if event_id:
            visit.google_event_id = event_id
            db.session.commit()
        flash("Visit scheduled and synced!", "success")
        return redirect(url_for('visits_list'))
    return render_template('visit_form.html', patients=patients, therapists=therapists)

@app.route('/visits/<int:visit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_visit(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    patients = Patient.query.all()
    therapists = Therapist.query.all()
    if request.method == 'POST':
        visit.patient_id = request.form.get('patient_id')
        visit.therapist_id = request.form.get('therapist_id')
        visit.visit_type = request.form.get('visit_type')
        visit_date = request.form.get('visit_date')
        visit_time = request.form.get('visit_time')
        visit.status = request.form.get('status')
        visit.visit_date = datetime.strptime(f"{visit_date} {visit_time}", "%m-%d-%Y %H:%M")
        visit.duration = 60
        db.session.commit()
        update_google_event(visit)
        flash("Visit updated!", "success")
        return redirect(url_for('visits_list'))
    return render_template('visit_form.html', visit=visit, patients=patients, therapists=therapists, edit=True)

@app.route('/visits/<int:visit_id>/delete', methods=['POST'])
@login_required
def delete_visit(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    delete_google_event(visit)
    db.session.delete(visit)
    db.session.commit()
    flash("Visit deleted (and removed from Google Calendar).", "info")
    return redirect(url_for('visits_list'))

    
# ========== PHYSICIAN, INSURANCE, BILLING ==========

@app.route('/therapists/new', methods=['GET', 'POST'])
@login_required
def new_therapist():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        credentials = request.form.get('credentials')
        email = request.form.get('email')
        phone = request.form.get('phone')
        availability = request.form.get('availability')

        # Basic validation (add more as needed)
        if not first_name or not last_name or not email:
            flash("First name, last name, and email are required.", "danger")
            return redirect(url_for('new_therapist'))

        therapist = Therapist(
            first_name=first_name,
            last_name=last_name,
            credentials=credentials,
            email=email,
            phone=phone,
            availability=availability
        )
        db.session.add(therapist)
        db.session.commit()
        flash("Therapist added!", "success")
        return redirect(url_for('therapists_list'))

    return render_template('therapist_form.html')

@app.route('/physicians/add', methods=['GET', 'POST'])
@login_required
def physicians_add():
    # Add your physician creation logic here
    return render_template('physician_form.html')
    
@app.route('/therapists')
@login_required
def therapists_list():
    therapists = Therapist.query.all()
    return render_template('therapists.html', therapists=therapists)
    
@app.route('/physicians')
@login_required
def physicians_list():
    physicians = Physician.query.all()
    return render_template('physicians.html', physicians=physicians)

@app.route('/insurance')
@login_required
def insurance_list():
    insurances = Insurance.query.all()
    return render_template('insurance_list.html', insurances=insurances)

@app.route('/billing')
@login_required
def billing_overview():
    return render_template('billing.html')

# ========== PT BUILDER & PATIENT PROFILE ==========
@app.route('/pt_builder')
@login_required
def pt_builder():
    return render_template('pt_builder.html')
    
@app.route('/patient/<int:patient_id>/pt_builder', methods=['GET'])
@login_required
def pt_builder_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    age = ""
    if patient.dob:
        try:
            if isinstance(patient.dob, str):
                birth = datetime.strptime(patient.dob, "%m-%d-%Y")
            else:
                birth = patient.dob
            today = datetime.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except Exception:
            age = ""
    return render_template('pt_builder_patient.html', patient=patient, age=age)
    
# ========== UPLOADS ==========
@app.route('/uploads', methods=['GET'])
@login_required
def uploads_list():
    attachments = Attachment.query.order_by(Attachment.uploaded_at.desc()).all()
    return render_template('uploads_list.html', attachments=attachments)

@app.route('/uploads/new', methods=['GET', 'POST'])
@login_required
def upload_file():
    patient_id = request.args.get('patient_id')  # Grab from URL if provided
    if request.method == 'POST':
        file = request.files.get('file')
        patient_id_form = request.form.get('patient_id') or patient_id
        visit_id = request.form.get('visit_id')
        if not file:
            flash("No file selected.", "danger")
            return redirect(url_for('upload_file', patient_id=patient_id))
        filename = file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        attachment = Attachment(
            filename=filename,
            filepath=save_path,
            patient_id=patient_id_form if patient_id_form else None,
            visit_id=visit_id if visit_id else None
        )
        db.session.add(attachment)
        db.session.commit()
        flash("File uploaded!", "success")
        # If you want to return to patient's profile after upload:
        if patient_id_form:
            return redirect(url_for('patient_profile', patient_id=patient_id_form))
        return redirect(url_for('uploads_list'))
    patients = Patient.query.all()
    visits = Visit.query.order_by(Visit.visit_date.desc()).all()
    return render_template('upload_form.html', patients=patients, visits=visits, selected_patient_id=patient_id)

@app.route('/uploads/<int:upload_id>/download')
@login_required
def download_file(upload_id):
    attachment = Attachment.query.get_or_404(upload_id)
    return send_file(attachment.filepath, as_attachment=True)

@app.route('/uploads/<int:upload_id>/delete', methods=['POST'])
@login_required
def delete_file(upload_id):
    attachment = Attachment.query.get_or_404(upload_id)
    try:
        if os.path.exists(attachment.filepath):
            os.remove(attachment.filepath)
        db.session.delete(attachment)
        db.session.commit()
        flash("File deleted.", "info")
    except Exception as e:
        flash(f"Error deleting file: {e}", "danger")
    # Redirect to patient profile if possible, else uploads list
    if attachment.patient_id:
        return redirect(url_for('patient_profile', patient_id=attachment.patient_id))
    return redirect(url_for('uploads_list'))
    
# ====== PT Section ======

PT_TEMPLATES = {
    "LBP Eval": {
        "meddiag": "",
        "history": "",
        "subjective": "Pt reports having LBP and is limiting daily functional activities. Pt would like to decrease pain and improve activity tolerance and return to PLOF. Pt agrees to PT evaluation.",
        "pain_location": "L-spine paraspinal, B QL, B gluteus medius",
        "pain_onset": "Chronic",
        "pain_condition": "Chronic",
        "pain_mechanism": "Muscle tension, stenosis, increased tone, structural changes",
        "pain_rating": "5/10, 0/10, 7/10",
        "pain_frequency": "Intermittent",
        "pain_description": "Sharp, Tense, Aching.",
        "pain_aggravating": "Sitting, standing, walking, forward bending, lifting/pulling.",
        "pain_relieved": "Pain meds prn and rest.",
        "pain_interferes": "Functional mobility, ADLs, sleep.",
        "meds": "See medication list",
        "tests": "N/A",
        "dme": "N/A",
        "plof": "Independent with mobility and ADLs",
        "posture": "Forward head lean, rounded shoulders, protracted scapular, slouch posture, decrease sitting postural awareness, loss of lumbar lordosis.",
        "rom": "Trunk Flexion: 50% limited\nTrunk Extension: 50% limited\nTrunk SB Left: 50% limited\nTrunk SB Right: 50% limited\nTrunk Rotation Left: 50% limited\nTrunk Rotation Right: 50% limited",
        "strength": "Gross Core Strength: 3/5\nGross Hip Strength: L/R  3/5; 3/5\nGross Knee Strength: L/R  3/5; 3/5\nGross Ankle Strength: L/R  3/5; 3/5",
        "palpation": "TTP: B QL, B gluteus medius, B piriformis, B paraspinal.\nJoint hypomobility: L1-L5 with central PA.\nIncreased paraspinal and gluteus medius tone",
        "functional": "Supine Sit Up Test: Unable\n30 seconds Chair Sit to Stand: 6x w/ increase LBP\nSingle Leg Balance Test: B LE: <1 sec with loss of balance.\nSingle Heel Raises Test: Unremarkable\nWalking on Toes:\nWalking on Heels:\nFunctional Squat:",
        "special": "(-) Slump Test\n(-) Unilateral SLR Test\n(-) Double SLR\n(-) Spring/Central PA\n(-) Piriformis test\n(-) SI Cluster Test",
        "impairments": "Prolonged sitting: 5 min\nStanding: 5 min\nWalking: 5 min\nBending, sweeping, cleaning, lifting: 5 min.",
        "goals": "Short-Term Goals (1–12 visits):\n1. Pt will report a reduction in low back pain to ≤1/10 to allow comfortable participation in functional activities.\n2. Pt will demonstrate a ≥10% improvement in trunk AROM to enhance mobility and reduce risk of reinjury during daily tasks.\n3. Pt will improve gross LE strength by at least 0.5 muscle grade to enhance safety during ADLs and minimize pain/injury risk.\n4. Pt will self-report ≥50% improvement in functional limitations related to ADLs.\nLong-Term Goals (13–25 visits):\n1. Pt will demonstrate B LE strength of ≥4/5 to independently and safely perform all ADLs.\n2. Pt will complete ≥14 repetitions on the 30-second chair sit-to-stand test to reduce fall risk.\n3. Pt will tolerate ≥30 minutes of activity to safely resume household tasks without limitation.\n4. Pt will demonstrate independence with HEP, using proper body mechanics and strength to support safe return to ADLs without difficulty.",
        "frequency": "1wk1, 2wk12",
        "intervention": "Manual Therapy (STM/IASTM/Joint Mob), Therapeutic Exercise, Therapeutic Activities, Neuromuscular Re-education, Gait Training, Balance Training, Pain Management Training, Modalities ice/heat 10-15min, E-Stim, Ultrasound, fall/injury prevention training, safety education/training, HEP education/training.",
        "procedures": "97161 Low Complexity\n97162 Moderate Complexity\n97163 High Complexity\n97140 Manual Therapy\n97110 Therapeutic Exercise\n97530 Therapeutic Activity\n97112 Neuromuscular Re-ed\n97116 Gait Training"
    },
    "Knee TKA Eval": {
        "meddiag": "",
        "history": "",
        "subjective": "Pt states s/p TKA and agreeable to PT evaluation. Pt reports having pain and swelling to the knee region and hasn't been using ice too much.",
        "pain_location": "Knee",
        "pain_onset": "",
        "pain_condition": "Acute",
        "pain_mechanism": "Post op swelling due to surgery",
        "pain_rating": "5/10, 3/10, 7/10",
        "pain_frequency": "Intermittent",
        "pain_description": "Sharp, Tension, Aching, dull/heaviness",
        "pain_aggravating": "Sitting, standing, walking, bed mobility.",
        "pain_relieved": "Pain meds prn, ice, rest, elevation",
        "pain_interferes": "Functional mobility, ADLs, sleep.",
        "meds": "See medication list",
        "tests": "N/A",
        "dme": "FWW",
        "plof": "Independent with mobility and ADLs.",
        "posture": "Forward head lean, rounded shoulders, protracted scapular, slouch posture, decrease sitting postural awareness, loss of lumbar lordosis.",
        "rom": "Hip Gross: WNL / WNL\nKnee Flex: \nKnee Ext:\nAnkle Gross: WNL / WNL",
        "strength": "Hip Gross: 4/5 / 4/5\nKnee Flex: 3/5* / 3/5*\nKnee Ext: 3/5* / 3/5*\nAnkle Gross: 4/5 / 4/5",
        "palpation": "TTP: B Quads, hamstring, knee swelling, warmth, tenderness periarticular",
        "functional": "Bed Mobility: SBA\n30 seconds Chair Sit to Stand: 2x w/ Knee pain\nSLB Test: Unable loss of balance\nSingle Heel Raises Test: 50% from full range, guarding at knee\nFunctional Squat: Unable",
        "special": "NT",
        "impairments": "Prolonged sitting: 5 min\nStanding: 5 min\nWalking: 5 min\nStep/stairs: 1 step",
        "goals": (
            "Short-Term Goals (1–12 visits):\n"
            "1. Pt will report a reduction in knee pain to ≤1/10 to allow safe and comfortable participation in functional activities.\n"
            "2. Pt will demonstrate a ≥10% improvement in knee AROM to enhance mobility and reduce risk of reinjury during daily tasks.\n"
            "3. Pt will improve gross LE strength by at least 0.5 muscle grade to enhance safety during ADLs and minimize pain/injury risk.\n"
            "4. Pt will self-report ≥50% improvement in functional limitations related to ADLs.\n"
            "Long-Term Goals (13–25 visits):\n"
            "1. Pt will demonstrate B LE strength of ≥4/5 to independently and safely perform all ADLs.\n"
            "2. Pt will complete ≥14 repetitions on the 30-second chair sit-to-stand test to reduce fall risk.\n"
            "3. Pt will tolerate ≥30 minutes of activity to safely resume household tasks without limitation.\n"
            "4. Pt will demonstrate independence with HEP, using proper body mechanics and strength to support safe return to ADLs without difficulty."
        ),
        "frequency": "1wk1, 2wk12",
        "intervention": "Manual Therapy (STM/IASTM/Joint Mob), Therapeutic Exercise, Therapeutic Activities, Neuromuscular Re-education, Gait Training, Balance Training, Pain Management Training, Modalities ice/heat 10-15min, E-Stim, Ultrasound, fall/injury prevention training, safety education/training, HEP education/training.",
        "procedures": "97161 Low Complexity\n97162 Moderate Complexity\n97163 High Complexity\n97140 Manual Therapy\n97110 Therapeutic Exercise\n97530 Therapeutic Activity\n97112 Neuromuscular Re-ed\n97116 Gait Training"
    }
}

def pt_parse_template(template):
    key_map = {
        "Medical Diagnosis": "meddiag",
        "Medical History/HNP": "history",
        "Subjective": "subjective",
        "Current Medication(s)": "meds",
        "Diagnostic Test(s)": "tests",
        "DME/Assistive Device": "dme",
        "PLOF": "plof",
        "Posture": "posture",
        "ROM": "rom",
        "Muscle Strength Test": "strength",
        "Palpation": "palpation",
        "Functional Test(s)": "functional",
        "Special Test(s)": "special",
        "Current Functional Mobility Impairment(s)": "impairments",
        "Goals": "goals",
        "Frequency/Duration": "frequency",
        "Intervention": "intervention",
        "Treatment Procedures": "procedures",
        "Area/Location of Injury": "pain_location",
        "Onset/Exacerbation Date": "pain_onset",
        "Condition of Injury": "pain_condition",
        "Mechanism of Injury": "pain_mechanism",
        "Pain Rating (P/B/W)": "pain_rating",
        "Pain Frequency": "pain_frequency",
        "Description": "pain_description",
        "Aggravating Factor": "pain_aggravating",
        "Relieved By": "pain_relieved",
        "Interferes With": "pain_interferes"
    }
    fields = {v: "" for v in key_map.values()}
    curr = None
    for line in template.splitlines():
        stripped = line.strip()
        matched = False
        for label, key in key_map.items():
            if stripped.startswith(label + ":"):
                curr = key
                _, val = stripped.split(":", 1)
                fields[key] = val.strip()
                matched = True
                break
        if not matched and curr and stripped:
            fields[curr] += "\n" + stripped
    return fields

@app.route("/pt_load_template", methods=["POST"])
@login_required
def pt_load_template():
    data = request.get_json()
    template_name = data.get("template", "")
    if not template_name:
        return jsonify(list(PT_TEMPLATES.keys()))
    else:
        return jsonify(PT_TEMPLATES.get(template_name, {}))


@app.route('/pt_export_word', methods=['POST'])
@login_required
def pt_export_word():
    data = request.json
    doc = pt_export_to_word(data)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name='PT_Eval.docx'
    )

def pt_export_to_word(data):
    doc = Document()
    def add_separator():
        doc.add_paragraph('-' * 114)
    doc.add_paragraph(f"Medical Diagnosis: {data.get('meddiag', '')}")
    add_separator()
    doc.add_paragraph(f"Medical History/HNP:\n{data.get('history', '')}")
    add_separator()
    doc.add_paragraph(f"Subjective:\n{data.get('subjective', '')}")
    add_separator()
    doc.add_paragraph("Pain:")
    pain_fields = [
        ("Area/Location of Injury", "pain_location"),
        ("Onset/Exacerbation Date", "pain_onset"),
        ("Condition of Injury", "pain_condition"),
        ("Mechanism of Injury", "pain_mechanism"),
        ("Pain Rating (Present/Best/Worst)", "pain_rating"),
        ("Frequency", "pain_frequency"),
        ("Description", "pain_description"),
        ("Aggravating Factor", "pain_aggravating"),
        ("Relieved By", "pain_relieved"),
        ("Interferes With", "pain_interferes"),
    ]
    for label, key in pain_fields:
        doc.add_paragraph(f"{label}: {data.get(key, '')}")
    doc.add_paragraph(f"Current Medication(s): {data.get('meds', '')}")
    doc.add_paragraph(f"Diagnostic Test(s): {data.get('tests', '')}")
    doc.add_paragraph(f"DME/Assistive Device: {data.get('dme', '')}")
    doc.add_paragraph(f"PLOF: {data.get('plof', '')}")
    add_separator()
    doc.add_paragraph("Objective:")
    obj_fields = [
        ("Posture", "posture"),
        ("ROM", "rom"),
        ("Muscle Strength Test", "strength"),
        ("Palpation", "palpation"),
        ("Functional Test(s)", "functional"),
        ("Special Test(s)", "special"),
        ("Current Functional Mobility Impairment(s)", "impairments"),
    ]
    for label, key in obj_fields:
        doc.add_paragraph(f"{label}:")
        doc.add_paragraph(f"{data.get(key, '')}")
    add_separator()
    doc.add_paragraph("Assessment Summary:")
    doc.add_paragraph(data.get('summary', ''))
    add_separator()
    doc.add_paragraph("Goals:")
    doc.add_paragraph(data.get('goals', ''))
    add_separator()
    doc.add_paragraph("Frequency:")
    doc.add_paragraph(data.get('frequency', ''))
    add_separator()
    doc.add_paragraph("Intervention:")
    doc.add_paragraph(data.get('intervention', ''))
    add_separator()
    doc.add_paragraph("Treatment Procedures:")
    doc.add_paragraph(data.get('procedures', ''))
    add_separator()
    return doc

@app.route("/pt_export_pdf", methods=["POST"])
@login_required
def pt_export_pdf():
    data = request.get_json()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40

    def add_section(title, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 13)
        c.drawString(40, y, title)
        y -= 18
        c.setFont("Helvetica", 11)
        for line in (value or "").split('\n'):
            c.drawString(48, y, line)
            y -= 14
            if y < 60:
                c.showPage()
                y = height - 40
        y -= 8
        c.setLineWidth(0.5)
        c.line(40, y, width - 40, y)
        y -= 16

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Physical Therapy Evaluation")
    y -= 30

    add_section("Medical Diagnosis:", data.get("meddiag", ""))
    add_section("Medical History/HNP:", data.get("history", ""))
    add_section("Subjective:", data.get("subjective", ""))
    pain_lines = [
        f"Area/Location of Injury: {data.get('pain_location','')}",
        f"Onset/Exacerbation Date: {data.get('pain_onset','')}",
        f"Condition of Injury: {data.get('pain_condition','')}",
        f"Mechanism of Injury: {data.get('pain_mechanism','')}",
        f"Pain Rating (Present/Best/Worst): {data.get('pain_rating','')}",
        f"Frequency: {data.get('pain_frequency','')}",
        f"Description: {data.get('pain_description','')}",
        f"Aggravating Factor: {data.get('pain_aggravating','')}",
        f"Relieved By: {data.get('pain_relieved','')}",
        f"Interferes With: {data.get('pain_interferes','')}",
        "",
        f"Current Medication(s): {data.get('meds','')}",
        f"Diagnostic Test(s): {data.get('tests','')}",
        f"DME/Assistive Device: {data.get('dme','')}",
        f"PLOF: {data.get('plof','')}",
    ]
    add_section("Pain:", "\n".join(pain_lines))
    obj_lines = [
        f"Posture: {data.get('posture','')}",
        "",
        f"ROM: \n{data.get('rom','')}",
        "",
        f"Muscle Strength Test: \n{data.get('strength','')}",
        "",
        f"Palpation: \n{data.get('palpation','')}",
        "",
        f"Functional Test(s): \n{data.get('functional','')}",
        "",
        f"Special Test(s): \n{data.get('special','')}",
        "",
        f"Current Functional Mobility Impairment(s): \n{data.get('impairments','')}",
    ]
    add_section("Objective:", "\n".join(obj_lines))
    add_section("Assessment Summary:", data.get("summary", ""))
    add_section("Goals:", data.get("goals", ""))
    add_section("Frequency:", data.get("frequency", ""))
    add_section("Intervention:", data.get("intervention", ""))
    add_section("Treatment Procedures:", data.get("procedures", ""))

    c.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="PT_Eval.pdf",
        mimetype="application/pdf"
    )

# ====== OT Section ======

OT_TEMPLATES = {
    "OT Eval Template": """Medical Diagnosis:
Medical History/HNP:
Subjective: Pt reports upper extremity pain and is limiting ADLs. Pt would like to improve function and return to PLOF. Pt agrees to OT evaluation.
Pain:
Area/Location of Injury: R shoulder
Onset/Exacerbation Date: 3 weeks ago
Condition of Injury: Acute on chronic
Mechanism of Injury: Lifting
Pain Rating (P/B/W): 4/10, 1/10, 7/10
Pain Frequency: Intermittent
Description: Sharp, throbbing
Aggravating Factor: Overhead activity, reaching
Relieved By: Rest, ice
Interferes With: Grooming, dressing, bathing

Current Medication(s): See medication list

Diagnostic Test(s): MRI right shoulder

DME/Assistive Device: None

PLOF: Independent

Posture: Forward head, rounded shoulders

ROM: R shoulder flexion 100°, abduction 80°

Muscle Strength Test: R shoulder 3+/5

Palpation: TTP R supraspinatus

Functional Test(s): Unable to reach overhead

Special Test(s): (+) Impingement

Current Functional Mobility Impairment(s): Reaching, overhead activity

Goals:
Short-Term Goals (1–12 visits):
1. Pt will decrease pain to ≤2/10 during ADLs.
2. Pt will improve R shoulder ROM to 140° flexion.
3. Pt will improve strength to 4/5.
4. Pt will perform ADLs independently.

Long-Term Goals (13–25 visits):
1. Pt will maintain pain ≤1/10 with all activity.
2. Pt will achieve full ROM and strength in R shoulder.
3. Pt will return to all prior ADLs independently.
4. Pt will independently complete HEP.

Frequency/Duration: 2x/wk x 6wks

Intervention: Manual Therapy, TherEx, HEP training, ADL retraining

Treatment Procedures:
97165 OT Eval
97110 Ther Ex
97530 Ther Activity
97535 Self-care Mgmt
"""
}

def ot_parse_template(template):
    key_map = {
        "Medical Diagnosis": "ot_meddiag",
        "Medical History/HNP": "ot_history",
        "Subjective": "ot_subjective",
        "Current Medication(s)": "ot_meds",
        "Diagnostic Test(s)": "ot_tests",
        "DME/Assistive Device": "ot_dme",
        "PLOF": "ot_plof",
        "Posture": "ot_posture",
        "ROM": "ot_rom",
        "Muscle Strength Test": "ot_strength",
        "Palpation": "ot_palpation",
        "Functional Test(s)": "ot_functional",
        "Special Test(s)": "ot_special",
        "Current Functional Mobility Impairment(s)": "ot_impairments",
        "Goals": "ot_goals",
        "Frequency/Duration": "ot_frequency",
        "Intervention": "ot_intervention",
        "Treatment Procedures": "ot_procedures",
        "Area/Location of Injury": "ot_pain_location",
        "Onset/Exacerbation Date": "ot_pain_onset",
        "Condition of Injury": "ot_pain_condition",
        "Mechanism of Injury": "ot_pain_mechanism",
        "Pain Rating (P/B/W)": "ot_pain_rating",
        "Pain Frequency": "ot_pain_frequency",
        "Description": "ot_pain_description",
        "Aggravating Factor": "ot_pain_aggravating",
        "Relieved By": "ot_pain_relieved",
        "Interferes With": "ot_pain_interferes"
    }
    fields = {v: "" for v in key_map.values()}
    curr = None
    for line in template.splitlines():
        stripped = line.strip()
        matched = False
        for label, key in key_map.items():
            if stripped.startswith(label + ":"):
                curr = key
                _, val = stripped.split(":", 1)
                fields[key] = val.strip()
                matched = True
                break
        if not matched and curr and stripped:
            fields[curr] += "\n" + stripped
    return fields

@app.route("/ot_load_template", methods=["POST"])
@login_required
def ot_load_template():
    name = request.json.get("template", "")
    text = OT_TEMPLATES.get(name, "")
    return jsonify(ot_parse_template(text))

@app.route("/pt_generate_diffdx", methods=["POST"])
@login_required
def pt_generate_diffdx():
    f = request.json.get("fields", {})
    pain = "; ".join(f"{lbl}: {f.get(key,'')}"
                      for lbl,key in [
                          ("Area/Location", "pain_location"),
                          ("Onset", "pain_onset"),
                          ("Condition", "pain_condition"),
                          ("Mechanism", "pain_mechanism"),
                          ("Rating", "pain_rating"),
                          ("Frequency", "pain_frequency"),
                          ("Description", "pain_description"),
                          ("Aggravating", "pain_aggravating"),
                          ("Relieved", "pain_relieved"),
                          ("Interferes", "pain_interferes"),
                      ])
    prompt = (
        "You are a PT clinical assistant. Provide the single best-fit diagnosis Keep it clean.:\n\n"
        f"Subjective:\n{f.get('subjective','')}\n\n"
        f"Pain:\n{pain}\n\n"
        f"Objective:\nPosture: {f.get('posture','')}\n"
        f"ROM: {f.get('rom','')}\n"
        f"Strength: {f.get('strength','')}\n"
    )
    result = gpt_call(prompt, max_tokens=200)
    return jsonify({"result": result})


@app.route("/pt_generate_summary", methods=["POST"])
@login_required
def pt_generate_summary():
    f = request.json.get("fields", {})
    name = f.get("name", "Pt Name")
    age = f.get("age", "X")
    gender = f.get("gender", "patient").lower()
    pmh = f.get("history", "no significant history")
    today = f.get("currentdate", date.today().strftime("%m/%d/%Y"))
    subj = f.get("subjective", "")
    moi = f.get("pain_mechanism", "")
    dx = f.get("diffdx", "")
    strg = f.get("strength", "")
    rom = f.get("rom", "")
    impair = f.get("impairments", "")
    func = f.get("functional", "")

    prompt = (
        "Generate a concise, 7-8 sentence Physical Therapy assessment summary medicare compliant form for PT documentation. "
        "Use clinical, professional language and use abbreviations only (e.g., HEP, ADLs, LBP, STM, TherEx, etc.; "
        "do not spell out the abbreviation and do not write both full term and abbreviation). "
        "Never use the phrase 'The patient'; instead, use 'Pt' at the start of each relevant sentence. "
        f"Start with: \"{name}, a {age} y/o {gender} with relevant history of {pmh}.\" "
        f"Include: "
        f"How/when/why pt was seen (PT initial eval on {today} for {subj}), "
        f"mechanism of injury if available ({moi}), "
        f"main differential dx ({dx}), "
        f"current impairments (strength: {strg}; ROM: {rom}; balance/mobility: {impair}), "
        f"functional/activity/participation limitations: {func}, "
        "a professional prognosis and that skilled PT will help pt return to PLOF. "
        "Do not use bulleted or numbered lists—just a single, well-written summary paragraph."
    )
    result = gpt_call(prompt, max_tokens=350)
    return jsonify({"result": result})


@app.route("/pt_generate_goals", methods=["POST"])
@login_required
def pt_generate_goals():
    # Get all eval fields (dictionary)
    fields = request.json.get("fields", {})
    # Make eval info readable for GPT
    eval_info = '\n'.join([f"{k}: {v}" for k, v in fields.items() if v])

    prompt = f"""
You are a clinical assistant helping a PT write documentation.
Using ONLY the provided eval info (summary, objective findings, strength, ROM, impairments, and functional limitations),
generate clinically-appropriate, Medicare-compliant short-term and long-term PT goals.
ALWAYS follow this exact format—do not add, skip, reorder, or alter any lines or labels.
DO NOT add any explanations, introductions, dashes, bullets, or extra indentation. Output ONLY this structure:

Short-Term Goals (1–12 visits):
1. [goal statement]
2. [goal statement]
3. [goal statement]
4. [goal statement]

Long-Term Goals (13–25 visits):
1. [goal statement]
2. [goal statement]
3. [goal statement]
4. [goal statement]

Replace [goal statement] with individualized goals based on eval info below.

Eval info:
{eval_info}
"""

    # Call your GPT function (replace with your real function if different)
    result = gpt_call(prompt, max_tokens=350)

    # Clean up any dashes or spaces before the section headers (just in case)
    result = result.replace('- Short-Term Goals', 'Short-Term Goals')
    result = result.replace('- Long-Term Goals', 'Long-Term Goals')
    result = re.sub(r'^\s+', '', result, flags=re.MULTILINE)

    return jsonify({"result": result})

@app.route('/pt_generate_daily_summary', methods=['POST'])
@login_required
def pt_generate_daily_summary():
    data = request.json
    prompt = (
        "You are a physical therapist. "
        "Write a 6-sentence daily PT note summary in paragraph form. "
        "Use professional tone, refer to 'patient' (not 'the patient' or 'patient reported'). "
        "Summarize the following:\n"
        f"Diagnosis: {data.get('diagnosis','')}\n"
        f"Interventions: {data.get('interventions','')}\n"
        f"Tx Tolerance: {data.get('tolerance','')}\n"
        f"Current Progress: {data.get('progress','')}\n"
        f"Next Visit Plan: {data.get('plan','')}\n"
        "Do not use the phrases 'patient reported' or 'the patient'. "
        "Do not spell out, use abbreviation only, avoid using both next to each other. "
        "After summarizes skip a row write a 1-2 sentences for next visit plan of care utilizing something along Focusing on PT POC to improve strength, endurance, mechanics, activity tolerance with manual therapy, ther-ex, ther-act, IASTM. Improve activity tolerance to return to safe ADLs and community participation and ambulation."
    )
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250
        )
        summary = completion.choices[0].message.content.strip()
        return jsonify({"result": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route('/ot_export_word', methods=['POST'])
@login_required
def ot_export_word():
    data = request.json
    doc = ot_export_to_word(data)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name='OT_Eval.docx'
    )

def ot_export_to_word(data):
    doc = Document()
    def add_separator():
        doc.add_paragraph('-' * 114)
    doc.add_paragraph(f"Medical Diagnosis: {data.get('ot_meddiag', '')}")
    add_separator()
    doc.add_paragraph(f"Medical History/HNP:\n{data.get('ot_history', '')}")
    add_separator()
    doc.add_paragraph(f"Subjective:\n{data.get('ot_subjective', '')}")
    add_separator()
    doc.add_paragraph("Pain:")
    pain_fields = [
        ("Area/Location of Injury", "ot_pain_location"),
        ("Onset/Exacerbation Date", "ot_pain_onset"),
        ("Condition of Injury", "ot_pain_condition"),
        ("Mechanism of Injury", "ot_pain_mechanism"),
        ("Pain Rating (Present/Best/Worst)", "ot_pain_rating"),
        ("Frequency", "ot_pain_frequency"),
        ("Description", "ot_pain_description"),
        ("Aggravating Factor", "ot_pain_aggravating"),
        ("Relieved By", "ot_pain_relieved"),
        ("Interferes With", "ot_pain_interferes"),
    ]
    for label, key in pain_fields:
        doc.add_paragraph(f"{label}: {data.get(key, '')}")
    doc.add_paragraph(f"Current Medication(s): {data.get('ot_meds', '')}")
    doc.add_paragraph(f"Diagnostic Test(s): {data.get('ot_tests', '')}")
    doc.add_paragraph(f"DME/Assistive Device: {data.get('ot_dme', '')}")
    doc.add_paragraph(f"PLOF: {data.get('ot_plof', '')}")
    add_separator()
    doc.add_paragraph("Objective:")
    obj_fields = [
        ("Posture", "ot_posture"),
        ("ROM", "ot_rom"),
        ("Muscle Strength Test", "ot_strength"),
        ("Palpation", "ot_palpation"),
        ("Functional Test(s)", "ot_functional"),
        ("Special Test(s)", "ot_special"),
        ("Current Functional Mobility Impairment(s)", "ot_impairments"),
    ]
    for label, key in obj_fields:
        doc.add_paragraph(f"{label}:")
        doc.add_paragraph(f"{data.get(key, '')}")
    add_separator()
    doc.add_paragraph("Assessment Summary:")
    doc.add_paragraph(data.get('ot_summary', ''))
    add_separator()
    doc.add_paragraph("Goals:")
    doc.add_paragraph(data.get('ot_goals', ''))
    add_separator()
    doc.add_paragraph("Frequency:")
    doc.add_paragraph(data.get('ot_frequency', ''))
    add_separator()
    doc.add_paragraph("Intervention:")
    doc.add_paragraph(data.get('ot_intervention', ''))
    add_separator()
    doc.add_paragraph("Treatment Procedures:")
    doc.add_paragraph(data.get('ot_procedures', ''))
    add_separator()
    return doc

@app.route("/ot_export_pdf", methods=["POST"])
@login_required
def ot_export_pdf():
    data = request.get_json()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40

    def add_section(title, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 13)
        c.drawString(40, y, title)
        y -= 18
        c.setFont("Helvetica", 11)
        for line in (value or "").split('\n'):
            c.drawString(48, y, line)
            y -= 14
            if y < 60:
                c.showPage()
                y = height - 40
        y -= 8
        c.setLineWidth(0.5)
        c.line(40, y, width - 40, y)
        y -= 16

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Occupational Therapy Evaluation")
    y -= 30

    add_section("Medical Diagnosis:", data.get("ot_meddiag", ""))
    add_section("Medical History/HNP:", data.get("ot_history", ""))
    add_section("Subjective:", data.get("ot_subjective", ""))
    pain_lines = [
        f"Area/Location of Injury: {data.get('ot_pain_location','')}",
        f"Onset/Exacerbation Date: {data.get('ot_pain_onset','')}",
        f"Condition of Injury: {data.get('ot_pain_condition','')}",
        f"Mechanism of Injury: {data.get('ot_pain_mechanism','')}",
        f"Pain Rating (Present/Best/Worst): {data.get('ot_pain_rating','')}",
        f"Frequency: {data.get('ot_pain_frequency','')}",
        f"Description: {data.get('ot_pain_description','')}",
        f"Aggravating Factor: {data.get('ot_pain_aggravating','')}",
        f"Relieved By: {data.get('ot_pain_relieved','')}",
        f"Interferes With: {data.get('ot_pain_interferes','')}",
        "",
        f"Current Medication(s): {data.get('ot_meds','')}",
        f"Diagnostic Test(s): {data.get('ot_tests','')}",
        f"DME/Assistive Device: {data.get('ot_dme','')}",
        f"PLOF: {data.get('ot_plof','')}",
    ]
    add_section("Pain:", "\n".join(pain_lines))
    obj_lines = [
        f"Posture: {data.get('ot_posture','')}",
        "",
        f"ROM: \n{data.get('ot_rom','')}",
        "",
        f"Muscle Strength Test: \n{data.get('ot_strength','')}",
        "",
        f"Palpation: \n{data.get('ot_palpation','')}",
        "",
        f"Functional Test(s): \n{data.get('ot_functional','')}",
        "",
        f"Special Test(s): \n{data.get('ot_special','')}",
        "",
        f"Current Functional Mobility Impairment(s): \n{data.get('ot_impairments','')}",
    ]
    add_section("Objective:", "\n".join(obj_lines))
    add_section("Assessment Summary:", data.get("ot_summary", ""))
    add_section("Goals:", data.get("ot_goals", ""))
    add_section("Frequency:", data.get("ot_frequency", ""))
    add_section("Intervention:", data.get("ot_intervention", ""))
    add_section("Treatment Procedures:", data.get("ot_procedures", ""))

    c.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="OT_Eval.pdf",
        mimetype="application/pdf"
    )
    
# ========== GPT HELPER ==========

def gpt_call(prompt, max_tokens=350):
    if not client:
        return "OpenAI client not configured"
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI error: {e}"


# ========== MAIN ==========

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
