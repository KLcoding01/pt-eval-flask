import os
import io
from flask import Flask, request, jsonify, render_template, send_file
from dotenv import load_dotenv
from openai import OpenAI
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import date
from soap import generate_soap

load_dotenv()
app = Flask(__name__)

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
        "You are a PT clinical assistant. Provide the single best-fit diagnosis:\n\n"
        f"Subjective:\n{f.get('subjective','')}\n\n"
        f"Pain:\n{pain}\n\n"
        f"Objective:\nPosture: {f.get('posture','')}\n"
        f"ROM: {f.get('rom','')}\n"
        f"Strength: {f.get('strength','')}\n"
    )
    print("PROMPT:", prompt)  # Log the prompt for debugging
    result = gpt_call(prompt, max_tokens=200)
    print("RESULT:", repr(result))  # Print exactly what is returned
    return result

@app.route("/generate_summary", methods=["POST"])
def generate_summary():
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
        "Generate a concise, 7-8 sentence Physical Therapy assessment summary for PT documentation. "
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
    return gpt_call(prompt, max_tokens=350)

@app.route("/generate_goals", methods=["POST"])
def generate_goals():
    f = request.json.get("fields", {})
    prompt = (
        "You are a clinical assistant helping a PT write documentation. Using the following information, generate short-term and long-term PT goals in this format (adapt based on the summary):\n"
        "Short-Term Goals (1–12 visits):\n"
        "1. Pt will report a reduction in low back pain to ≤1/10 to allow safe and comfortable participation in functional activities.\n"
        "2. Pt will demonstrate a ≥10% improvement in trunk AROM to enhance mobility and reduce risk of reinjury during daily tasks.\n"
        "3. Pt will improve gross LE strength by at least 0.5 muscle grade to enhance safety during ADLs and minimize pain/injury risk.\n"
        "4. Pt will self-report ≥50% improvement in functional limitations related to ADLs.\n"
        "Long-Term Goals (13–25 visits):\n"
        "1. Pt will demonstrate B LE strength of ≥4/5 to independently and safely perform all ADLs.\n"
        "2. Pt will complete ≥14 repetitions on the 30-second chair sit-to-stand test to reduce fall risk.\n"
        "3. Pt will tolerate ≥30 minutes of activity to safely resume household tasks without limitation.\n"
        "4. Pt will demonstrate independence with HEP, using proper body mechanics and strength to support safe return to ADLs without difficulty.\n\n"
        f"Summary: {f.get('summary','')}\nDiagnosis: {f.get('diffdx','')}\nImpairments: {f.get('impairments','')}\nFunctional Limitations: {f.get('functional','')}"
    )
    return gpt_call(prompt, max_tokens=350)
    
@app.route('/generate_soap_summary', methods=['POST'])
def generate_soap_summary_route():
    data = request.get_json()
    fields = data.get('fields', {})
    return generate_soap(fields, use_ai=True)
    
@app.route("/export_word", methods=["POST"])
def export_word():
    data = request.get_json()
    doc = Document()

    def add_section(title, content):
        doc.add_paragraph(title)
        doc.add_paragraph(content.strip() if content else "")

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

if __name__ == '__main__':
    app.run(debug=True)

