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

# OpenAI client (v1)
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

### TEMPLATES ###
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

def parse_template(template):
    fields = {k: "" for k in [
        "meddiag","history","subjective","meds","tests","dme","plof",
        "posture","rom","strength","palpation","functional","special",
        "impairments","goals","frequency","intervention","procedures",
        "pain_location","pain_onset","pain_condition","pain_mechanism",
        "pain_rating","pain_frequency","pain_description",
        "pain_aggravating","pain_relieved","pain_interferes"
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
            if line.startswith(k + ":"):
                curr = f
                fields[f] = line.split(":", 1)[1].strip()
                break
        else:
            if curr and line:
                fields[curr] += "\n" + line
    return fields

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", templates=list(TEMPLATES.keys()))

@app.route("/load_template", methods=["POST"])
def load_template():
    name = request.json.get("template", "")
    text = TEMPLATES.get(name, "")
    return jsonify(parse_template(text))

@app.route("/generate_diffdx", methods=["POST"])
def generate_diffdx():
    f = request.json.get("fields", {})
    hpi = f.get("subjective", "")
    pain = "; ".join(f"{l}: {f.get(k, '')}" for l,k in [
        ("Area/Location","pain_location"),("Onset","pain_onset"),
        ("Condition","pain_condition"),("Mechanism","pain_mechanism"),
        ("Rating","pain_rating"),("Frequency","pain_frequency"),
        ("Description","pain_description"),("Aggravating","pain_aggravating"),
        ("Relieved","pain_relieved"),("Interferes","pain_interferes")
    ])
    obj = f"Posture: {f.get('posture','')}\nROM: {f.get('rom','')}\nStrength: {f.get('strength','')}\n"
    prompt = (
        "You are a PT clinical assistant. Provide the single best-fit diagnosis:\n\n"
        f"Subjective:\n{hpi}\n\nPain:\n{pain}\n\nObjective:\n{obj}"
    )
    return gpt_call(prompt, max_tokens=200), 200

@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    f = request.json.get("fields", {})
    prompt = (
        f'Generate a concise, 7-8 sentence PT assessment summary. '
        f'Start: "Pt {f.get("name","")} a {f.get("age","")} y/o {f.get("gender","").lower()} with relevant history of {f.get("history","")}". '
        f'Include: PT eval on {f.get("currentdate","")}, mechanism: {f.get("pain_mechanism","")}, '
        f'diff dx: {f.get("diffdx","")}, impairments: strength {f.get("strength","")}, ROM {f.get("rom","")}, '
        f'impair {f.get("impairments","")}, functional limits {f.get("functional","")}, prognosis, and skilled PT → return to PLOF.'
    )
    return gpt_call(prompt, max_tokens=350), 200

@app.route("/generate_goals", methods=["POST"])
def generate_goals():
    f = request.json.get("fields", {})
    prompt = (
        f"You are a clinical assistant. Generate short-term (1–12 visits) and long-term (13–25 visits) PT goals "
        f"based on:\nSummary: {f.get('summary','')}\nDiff Dx: {f.get('diffdx','')}\n"
        f"Impairments: {f.get('impairments','')}\nFunctional: {f.get('functional','')}"
    )
    return gpt_call(prompt, max_tokens=350), 200

@app.route("/export_word", methods=["POST"])
def export_word():
    d = request.get_json()
    doc = Document()
    doc.add_heading("Physical Therapy Evaluation", 0)
    def sec(t,v):
        doc.add_paragraph(t, style="Heading2")
        doc.add_paragraph(v or "", style="Normal")
        doc.add_paragraph("-"*100)
    sec("Medical Diagnosis:", d.get("meddiag",""))
    sec("Medical History/HNP:", d.get("history",""))
    sec("Subjective:", d.get("subjective",""))
    # ... similar for pain, objective, summary, goals ...
    buf = io.BytesIO()
    doc.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name="PT_Eval.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    d = request.get_json()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w,h = letter; y = h - 40
    def sec(t,v):
        nonlocal y
        c.setFont("Helvetica-Bold",12); c.drawString(40,y,t); y-=16
        c.setFont("Helvetica",10)
        for ln in (v or "").split("\n"):
            c.drawString(48,y,ln); y-=12
            if y<60: c.showPage(); y=h-40
        y-=8; c.line(40,y,w-40,y); y-=12
    sec("Medical Diagnosis:", d.get("meddiag",""))
    sec("Medical History/HNP:", d.get("history",""))
    sec("Subjective:", d.get("subjective",""))
    # ... continue for all sections ...
    c.save(); buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name="PT_Eval.pdf",
                     mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)
