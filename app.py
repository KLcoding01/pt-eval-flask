import os
from flask import Flask, request, send_file, render_template, jsonify
from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import date
from dotenv import load_dotenv
import io
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

# NEW: Create OpenAI client for v1
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

def gpt_call(prompt, max_tokens=350):
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"OpenAI error: {e}"

TEMPLATES = {
    "LBP Eval Template": """Medical Diagnosis:
Medical History/HNP:
Subjective: Pt reports having LBP and is limiting daily functional activities. Pt would like to decrease pain and improve activity tolerance and return to PLOF. Pt agrees to PT evaluation.
Pain:
Area/Location of Injury: L-spine paraspinal, B QL, B gluteus medius
Onset/Exacerbation Date: Chronic
Condition of Injury: Chronic
Mechanism of Injury: Muscle tension, stenosis, increased tone, structural changes
Pain Rating (P/B/W): 5/10, 0/10, 7/10
Pain Frequency: Intermittent
Description: Sharp, Tense, Aching.
Aggravating Factor: Sitting, standing, walking, forward bending, lifting/pulling.
Relieved By: Pain meds prn and rest.
Interferes With: Functional mobility, ADLs, sleep.

Current Medication(s): See medication list

Diagnostic Test(s): N/A

DME/Assistive Device: N/A

PLOF: Independent with mobility and ADLs

Posture: Forward head lean, rounded shoulders, protracted scapular, slouch posture, decrease sitting postural awareness, loss of lumbar lordosis.

ROM:
    Trunk Flexion: 50% limited
    Trunk Extension: 50% limited
    Trunk SB Left: 50% limited
    Trunk SB Right: 50% limited
    Trunk Rotation Left: 50% limited
    Trunk Rotation Right: 50% limited

Muscle Strength Test:          
     Gross Core Strength:        3/5
     Gross Hip Strength:    L/R  3/5; 3/5
     Gross Knee Strength:   L/R  3/5; 3/5
     Gross Ankle Strength:  L/R  3/5; 3/5

Palpation:
     TTP: B QL, B gluteus medius, B piriformis, B paraspinal.
     Joint hypomobility: L1-L5 with central PA.
     Increased paraspinal and gluteus medius tone

Functional Test(s):
     Supine Sit Up Test:  Unable
     30 seconds Chair Sit to Stand: 6x w/ increase LBP
     Single Leg Balance Test: B LE: <1 sec with loss of balance.
     Single Heel Raises Test: Unremarkable
     Walking on Toes:
     Walking on Heels:
     Functional Squat:

Special Test(s):
     (-) Slump Test
     (-) Unilateral SLR Test
     (-) Double SLR
     (-) Spring/Central PA
     (-) Piriformis test
     (-) SI Cluster Test

Current Functional Mobility Impairment(s):
     Prolonged sitting: 5 min
     Standing: 5 min
     Walking: 5 min
     Bending, sweeping, cleaning, lifting: 5 min.

Goals:
Short-Term Goals (1–12 visits):
1. Pt will report a reduction in low back pain to ≤1/10 to allow safe and comfortable participation in functional activities.
2. Pt will demonstrate a ≥10% improvement in trunk AROM to enhance mobility and reduce risk of reinjury during daily tasks.
3. Pt will improve gross LE strength by at least 0.5 muscle grade to enhance safety during ADLs and minimize pain/injury risk.
4. Pt will self-report ≥50% improvement in functional limitations related to ADLs.

Long-Term Goals (13–25 visits):
1. Pt will demonstrate B LE strength of ≥4/5 to independently and safely perform all ADLs.
2. Pt will complete ≥14 repetitions on the 30-second chair sit-to-stand test to reduce fall risk.
3. Pt will tolerate ≥30 minutes of activity to safely resume household tasks without limitation.
4. Pt will demonstrate independence with HEP, using proper body mechanics and strength to support safe return to ADLs without difficulty.

Frequency/Duration: 1wk1, 2wk12

Intervention: Manual Therapy (STM/IASTM/Joint Mob), Therapeutic Exercise, Therapeutic Activities, Neuromuscular Re-education, Gait Training, Balance Training, Pain Management Training, Modalities ice/heat 10-15min, E-Stim, Ultrasound, fall/injury prevention training, safety education/training, HEP education/training.

Treatment Procedures:
97161 Low Complexity
97162 Moderate Complexity
97163 High Complexity
97140 Manual Therapy
97110 Therapeutic Exercise
97530 Therapeutic Activity
97112 Neuromuscular Re-ed
97116 Gait Training
"""
}

# Helper: Parse template text into fields
def parse_template(template):
    fields = {k: "" for k in [
        "meddiag", "history", "subjective", "meds", "tests", "dme", "plof",
        "posture", "rom", "strength", "palpation", "functional", "special",
        "impairments", "goals", "frequency", "intervention", "procedures",
        "pain_location", "pain_onset", "pain_condition", "pain_mechanism",
        "pain_rating", "pain_frequency", "pain_description", "pain_aggravating",
        "pain_relieved", "pain_interferes"
    ]}
    key_map = {
        "Medical Diagnosis": "meddiag",
        "Medical History/HNP": "history",
        "Subjective": "subjective",
        "Subjective (HPI)": "subjective",
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
    curr = None
    for line in template.splitlines():
        line = line.strip()
        for k, f in key_map.items():
            if line.startswith(k+":"):
                curr = f
                fields[f] = line.split(":",1)[1].strip()
                break
        else:
            if curr and line: fields[curr] += "\n"+line
    return fields

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", templates=TEMPLATES)

@app.route("/load_template", methods=["POST"])
def load_template():
    data = request.json
    name = data.get("template", "LBP Eval Template")
    template = TEMPLATES.get(name, "")
    fields = parse_template(template)
    return jsonify(fields)

@app.route('/generate_diffdx', methods=['POST'])
def generate_diffdx():
    fields = request.json.get('fields', {})
    hpi  = fields.get("subjective", "")
    pain = "; ".join([
        f"{label}: {fields.get(key, '')}"
        for label, key in [
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
        ]
    ])
    obj = (
        f"Posture: {fields.get('posture', '')}\n"
        f"ROM: {fields.get('rom', '')}\n"
        f"Strength: {fields.get('strength', '')}\n"
    )
    prompt = (
        "You are a PT clinical assistant. Provide the single best-fit diagnosis:\n\n"
        f"Subjective:\n{hpi}\n\nPain:\n{pain}\n\nObjective:\n{obj}"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=200
    )
    diffdx = response.choices[0].message["content"].strip()
    return diffdx
    
@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    fields = request.json.get('fields', {})
    # Compose your prompt using your requirements
    prefix = ""
    name = fields.get("name", "Pt Name")
    age = fields.get("age", "X")
    gender = fields.get("gender", "patient")
    pmh = fields.get("history", "no significant history")
    today = fields.get("currentdate", "today")
    subj = fields.get("subjective", "")
    moi = fields.get("pain_mechanism", "")
    dx = fields.get("diffdx", "")
    strg = fields.get("strength", "")
    rom = fields.get("rom", "")
    impair = fields.get("impairments", "")
    func = fields.get("functional", "")
    prognosis = "good potential for improvement"  # You may pull from elsewhere

    prompt = f"""Generate a concise, 7-8 sentence Physical Therapy assessment summary for PT documentation. Use clinical, professional language and use abbreviations only (e.g., use HEP, ADLs, LBP, STM, TherEx, etc.—do not spell out the abbreviation and do not write both full term and abbreviation). Never use the phrase 'The patient'; instead, use 'Pt' at the start of each relevant sentence. Start with: "{prefix} {name}, a {age} y/o {gender.lower()} with relevant history of {pmh}." 
Include: 
1) How/when/why pt was seen (PT initial eval on {today} for {subj}), 
2) mechanism of injury if available ({moi}),
3) main differential dx ({dx}),
4) current impairments (strength: {strength}; ROM: {rom}; balance/mobility: {impairments}), 
5) functional/activity/participation limitations: {func},
6) a professional prognosis and 
7) that skilled PT will help pt return to PLOF.
Do not use bulleted or numbered lists—just a single, well-written summary paragraph."""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=350
    )
    summary = response.choices[0].message["content"].strip()
    return summary
    
@app.route("/generate_goals", methods=["POST"])
def generate_goals():
    data = request.json
    fields = data.get("fields", {})
    prompt = f"""
You are a clinical assistant helping a PT write documentation. Using the following information, generate short-term and long-term PT goals in this format (adapt based on the summary):
Short-Term Goals (1–12 visits):
1. Pt will report a reduction in low back pain to ≤1/10 to allow safe and comfortable participation in functional activities.
2. Pt will demonstrate a ≥10% improvement in trunk AROM to enhance mobility and reduce risk of reinjury during daily tasks.
3. Pt will improve gross LE strength by at least 0.5 muscle grade to enhance safety during ADLs and minimize pain/injury risk.
4. Pt will self-report ≥50% improvement in functional limitations related to ADLs.
Long-Term Goals (13–25 visits):
1. Pt will demonstrate B LE strength of ≥4/5 to independently and safely perform all ADLs.
2. Pt will complete ≥14 repetitions on the 30-second chair sit-to-stand test to reduce fall risk.
3. Pt will tolerate ≥30 minutes of activity to safely resume household tasks without limitation.
4. Pt will demonstrate independence with HEP, using proper body mechanics and strength to support safe return to ADLs without difficulty.

Summary: {fields.get('summary','')}
Diagnosis: {fields.get('diffdx','')}
Impairments: {fields.get('impairments','')}
Functional Limitations: {fields.get('functional','')}
"""
    goals = gpt_call(prompt, max_tokens=350)
    return goals

@app.route("/export_word", methods=["POST"])
def export_word():
    data = request.get_json()
    doc = Document()
    doc.add_heading("Physical Therapy Evaluation", 0)
    
    def add_section(title, value):
        doc.add_paragraph(title, style='Heading2')
        doc.add_paragraph(value if value else "", style='Normal')
        doc.add_paragraph('-'*114)

    # Section: Medical Diagnosis
    add_section("Medical Diagnosis:", data.get("meddiag", ""))
    # Section: Medical History/HNP
    add_section("Medical History/HNP:", data.get("history", ""))
    # Section: Subjective
    add_section("Subjective:", data.get("subjective", ""))
    # Section: Pain
    doc.add_paragraph("Pain:", style='Heading2')
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
    doc.add_paragraph('-'*114)
    # Medications, Tests, DME, PLOF
    add_section("Current Medication(s):", data.get("meds", ""))
    add_section("Diagnostic Test(s):", data.get("tests", ""))
    add_section("DME/Assistive Device:", data.get("dme", ""))
    add_section("PLOF:", data.get("plof", ""))

    # Objective
    doc.add_paragraph("Objective:", style='Heading2')
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
        doc.add_paragraph(f"{label}: {data.get(key, '')}")
    doc.add_paragraph('-'*114)

    # Assessment Summary
    add_section("Assessment Summary:", data.get("summary", ""))
    # Goals
    add_section("Goals:", data.get("goals", ""))
    # Frequency
    add_section("Frequency:", data.get("frequency", ""))
    # Intervention
    add_section("Intervention:", data.get("intervention", ""))
    # Procedures
    add_section("Treatment Procedures:", data.get("procedures", ""))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="PT_Eval.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.route("/export_pdf", methods=["POST"])
def export_pdf():
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
            if y < 60: c.showPage(); y = height - 40
        y -= 8
        c.setLineWidth(0.5)
        c.line(40, y, width - 40, y)
        y -= 16

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Physical Therapy Evaluation")
    y -= 30

    # Add all main sections in the same order
    add_section("Medical Diagnosis:", data.get("meddiag", ""))
    add_section("Medical History/HNP:", data.get("history", ""))
    add_section("Subjective:", data.get("subjective", ""))

    # Pain block
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Pain:")
    y -= 18
    c.setFont("Helvetica", 11)
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
        c.drawString(48, y, f"{label}: {data.get(key, '')}")
        y -= 14
        if y < 60: c.showPage(); y = height - 40
    y -= 8
    c.line(40, y, width - 40, y)
    y -= 16

    add_section("Current Medication(s):", data.get("meds", ""))
    add_section("Diagnostic Test(s):", data.get("tests", ""))
    add_section("DME/Assistive Device:", data.get("dme", ""))
    add_section("PLOF:", data.get("plof", ""))

    # Objective block
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Objective:")
    y -= 18
    c.setFont("Helvetica", 11)
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
        c.drawString(48, y, f"{label}: {data.get(key, '')}")
        y -= 14
        if y < 60: c.showPage(); y = height - 40
    y -= 8
    c.line(40, y, width - 40, y)
    y -= 16

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

if __name__ == '__main__':
    app.run(debug=True)
