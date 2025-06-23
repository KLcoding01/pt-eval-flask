import os
import io
from flask import Flask, request, render_template, jsonify, send_file
from dotenv import load_dotenv
from openai import OpenAI
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

load_dotenv()
app = Flask(__name__)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

def gpt_call(prompt, max_tokens=350):
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI error: {e}"

# Your LBP template (add more if you like)
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
     Gross Core Strength: 3/5
     Gross Hip Strength: L/R 3/5; 3/5
     Gross Knee Strength: L/R 3/5; 3/5
     Gross Ankle Strength: L/R 3/5; 3/5

Palpation:
     TTP: B QL, B gluteus medius, B piriformis, B paraspinal.
     Joint hypomobility: L1-L5 with central PA.
     Increased paraspinal and gluteus medius tone

Functional Test(s):
     Supine Sit Up Test: Unable
     30s Chair Sit-to-Stand: 6x w/ increase LBP
     Single Leg Balance Test: B LE: <1 sec
     Single Heel Raises: Unremarkable
     Functional Squat: N/A

Special Test(s):
     (-) Slump Test
     (-) SI Cluster

Current Functional Mobility Impairment(s):
     Prolonged sitting: 5 min
     Standing: 5 min
     Walking: 5 min

Goals:
Short-Term Goals (1–12 visits):
1. Pt will report a reduction in low back pain to ≤1/10...
2. Pt will demonstrate ≥10% improvement in trunk AROM...
3. Pt will improve gross LE strength by ≥0.5 muscle grade...
4. Pt will self-report ≥50% improvement in functional limitations.

Long-Term Goals (13–25 visits):
1. Pt will demonstrate B LE strength ≥4/5...
2. Pt will complete ≥14 reps on the 30-s chair sit-to-stand...
3. Pt will tolerate ≥30 min of activity without pain...
4. Pt will demonstrate independence with HEP...

Frequency/Duration: 1wk1, 2wk12

Intervention: STM/IASTM/Joint Mob, TherEx, TherAct, NMRe-ed, Gait & Balance Training, Modalities, HEP training.

Treatment Procedures:
97161, 97162, 97163, 97140, 97110, 97530, 97112, 97116
"""
}

def parse_template(template_text):
    # initialize every field we care about
    fields = {k: "" for k in [
        "meddiag","history","subjective","meds","tests","dme","plof",
        "posture","rom","strength","palpation","functional","special",
        "impairments","diffdx","summary","goals","frequency","intervention","procedures",
        "pain_location","pain_onset","pain_condition","pain_mechanism",
        "pain_rating","pain_frequency","pain_description",
        "pain_aggravating","pain_relieved","pain_interferes",
        "name","gender","dob","age","currentdate"
    ]}
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
        "Pain Rating": "pain_rating",
        "Pain Frequency": "pain_frequency",
        "Description": "pain_description",
        "Aggravating Factor": "pain_aggravating",
        "Relieved By": "pain_relieved",
        "Interferes With": "pain_interferes"
    }
    current = None
    for line in template_text.splitlines():
        line = line.strip()
        # detect new section
        for label, field_key in key_map.items():
            if line.startswith(label + ":"):
                current = field_key
                fields[field_key] = line.split(":",1)[1].strip()
                break
        else:
            # continuation of previous
            if current and line:
                fields[current] += "\n" + line
    return fields

@app.route("/")
def index():
    return render_template("index.html", templates=list(TEMPLATES.keys()))

@app.route("/load_template", methods=["POST"])
def load_template():
    name = request.json.get("template","")
    tmpl = TEMPLATES.get(name,"")
    data = parse_template(tmpl)
    return jsonify(data)

@app.route("/generate_diffdx", methods=["POST"])
def generate_diffdx():
    f = request.json.get("fields",{})
    hpi  = f.get("subjective","")
    pain = "; ".join(f"{lbl}: {f.get(k,'')}" for lbl,k in [
        ("Area/Location","pain_location"),
        ("Onset","pain_onset"),
        ("Condition","pain_condition"),
        ("Mechanism","pain_mechanism"),
        ("Rating","pain_rating"),
        ("Frequency","pain_frequency"),
        ("Description","pain_description"),
        ("Aggravating","pain_aggravating"),
        ("Relieved","pain_relieved"),
        ("Interferes","pain_interferes")
    ])
    obj = f"Posture: {f.get('posture','')}\nROM: {f.get('rom','')}\nStrength: {f.get('strength','')}\n"
    prompt = (
        "You are a PT clinical assistant. Provide the single best-fit diagnosis:\n\n"
        f"Subjective:\n{hpi}\n\nPain:\n{pain}\n\nObjective:\n{obj}"
    )
    result = gpt_call(prompt, max_tokens=200)
    return result, 200

@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    f = request.json.get("fields",{})
    prompt = (
        f"Generate a concise, 7-8 sentence PT assessment summary. Use clinical language and abbreviations (HEP, ADLs, LBP, etc.). "
        f"Start with: \"Pt {f.get('name','')} a {f.get('age','')} y/o {f.get('gender','').lower()} with relevant history of {f.get('history','')}\". "
        f"Include: initial eval on {f.get('currentdate','')}, moi: {f.get('pain_mechanism','')}, dx: {f.get('diffdx','')}, "
        f"impairments (str: {f.get('strength','')}; ROM: {f.get('rom','')}; impair: {f.get('impairments','')}), "
        f"limits: {f.get('functional','')}, prognosis, skilled PT return to PLOF. No lists."
    )
    return gpt_call(prompt), 200

@app.route("/generate_goals", methods=["POST"])
def generate_goals():
    f = request.json.get("fields",{})
    prompt = (
        f"You are a clinical assistant. Generate short-term and long-term PT goals based on:\n"
        f"Summary: {f.get('summary','')}\nDx: {f.get('diffdx','')}\nImpairments: {f.get('impairments','')}\nFunctional: {f.get('functional','')}"
    )
    return gpt_call(prompt), 200

@app.route("/export_word", methods=["POST"])
def export_word():
    data = request.get_json()
    doc = Document()
    doc.add_heading("Physical Therapy Evaluation",0)
    def sec(title, val):
        doc.add_paragraph(title, style="Heading2")
        doc.add_paragraph(val or "", style="Normal")
        doc.add_paragraph("-"*80)
    sec("Medical Diagnosis:", data.get("meddiag",""))
    sec("Medical History/HNP:", data.get("history",""))
    sec("Subjective:", data.get("subjective",""))
    # ... replicate for Pain, Objective, Summary, Goals, etc.
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True,
        download_name="PT_Eval.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    data = request.get_json()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w,h = letter; y=h-40
    def sec(title, val):
        nonlocal y
        c.setFont("Helvetica-Bold",12); c.drawString(40,y,title); y-=14
        c.setFont("Helvetica",10)
        for ln in (val or "").split("\n"):
            c.drawString(48,y,ln); y-=12
            if y<60: c.showPage(); y=h-40
        y-=8; c.line(40,y,w-40,y); y-=12
    sec("Medical Diagnosis:", data.get("meddiag",""))
    sec("Medical History/HNP:", data.get("history",""))
    sec("Subjective:", data.get("subjective",""))
    # ... replicate for other sections ...
    c.save(); buf.seek(0)
    return send_file(buf, as_attachment=True,
        download_name="PT_Eval.pdf", mimetype="application/pdf"
    )

if __name__=="__main__":
    app.run(debug=True)
