import os
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from datetime import date
import openai
from dotenv import load_dotenv
from io import BytesIO
from docx import Document

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"

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
    fields = {k:"" for k in [
        "med_diag","med_hist","subj","meds","tests","dme","plof","posture","rom","str","palpation","func",
        "special","impair","goals","freq","interv","proc","pain_area","pain_onset","pain_cond","pain_mech",
        "pain_rating","pain_freq","pain_desc","pain_aggrav","pain_relieve","pain_interfere"
    ]}
    key_map = {
        "Medical Diagnosis": "med_diag",
        "Medical History/HNP": "med_hist",
        "Subjective": "subj",
        "Current Medication(s)": "meds",
        "Diagnostic Test(s)": "tests",
        "DME/Assistive Device": "dme",
        "PLOF": "plof",
        "Posture": "posture",
        "ROM": "rom",
        "Muscle Strength Test": "str",
        "Palpation": "palpation",
        "Functional Test(s)": "func",
        "Special Test(s)": "special",
        "Current Functional Mobility Impairment(s)": "impair",
        "Goals": "goals",
        "Frequency/Duration": "freq",
        "Intervention": "interv",
        "Treatment Procedures": "proc",
        "Area/Location of Injury": "pain_area",
        "Onset/Exacerbation Date": "pain_onset",
        "Condition of Injury": "pain_cond",
        "Mechanism of Injury": "pain_mech",
        "Pain Rating (P/B/W)": "pain_rating",
        "Pain Frequency": "pain_freq",
        "Description": "pain_desc",
        "Aggravating Factor": "pain_aggrav",
        "Relieved By": "pain_relieve",
        "Interferes With": "pain_interfere"
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

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    selected_template = "LBP Eval Template"
    fields = {k:"" for k in [
        "name","gender","dob","age","today",
        "med_diag","med_hist","subj","meds","tests","dme","plof","posture","rom","str","palpation","func",
        "special","impair","diff","summary",
        "goals","freq","interv","proc",
        "pain_area","pain_onset","pain_cond","pain_mech",
        "pain_rating","pain_freq","pain_desc","pain_aggrav","pain_relieve","pain_interfere"
    ]}
    fields["today"] = date.today().strftime("%m-%d-%Y")
    if request.method == "POST":
        if "action" in request.form and request.form["action"] == "Load":
            selected_template = request.form.get("template", "LBP Eval Template")
            fields.update(parse_template(TEMPLATES[selected_template]))
            result = "Loaded template!"
        else:
            for k in fields: fields[k] = request.form.get(k,"")
            result = "Saved! (Or add DB/save logic here)"
    return render_template("index.html", templates=TEMPLATES, selected_template=selected_template, fields=fields, result=result)

@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    data = request.json or request.form
    prompt = f"""
Generate a concise, 7-8 sentence PT assessment summary for documentation using abbreviations only (HEP, ADLs, LBP, STM, TherEx, etc). Never use 'The patient', always start with 'Pt ...'.
Subj: {data.get('subj')}
Dx: {data.get('diff')}
Impairments: {data.get('impair')}
Function: {data.get('func')}
"""
    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return str(e), 500

@app.route("/download_word", methods=["POST"])
def download_word():
    data = request.form
    doc = Document()
    def add(label, key): doc.add_paragraph(f"{label} {data.get(key,'')}")
    add("Patient Name:", "name")
    add("Gender:", "gender")
    add("DOB:", "dob")
    add("Age:", "age")
    add("Today:", "today")
    doc.add_paragraph("-"*50)
    for field in ["med_diag","med_hist","subj","meds","tests","dme","plof"]:
        add(field.replace("_"," ").title()+":", field)
    doc.add_paragraph("-"*50)
    doc.add_paragraph("Pain Section:")
    for key in ["pain_area","pain_onset","pain_cond","pain_mech","pain_rating","pain_freq","pain_desc","pain_aggrav","pain_relieve","pain_interfere"]:
        add(key.replace("pain_","").replace("_"," ").title()+":", key)
    doc.add_paragraph("-"*50)
    for field in ["posture","rom","str","palpation","func","special","impair"]:
        add(field.title()+":", field)
    doc.add_paragraph("-"*50)
    add("Diff Dx:", "diff")
    add("Assessment Summary:", "summary")
    add("Goals:", "goals")
    add("Frequency:", "freq")
    add("Intervention:", "interv")
    add("Treatment Procedures:", "proc")
    f = BytesIO()
    doc.save(f)
    f.seek(0)
    return send_file(f, as_attachment=True, download_name="PT_Eval.docx")

if __name__ == "__main__":
    app.run(debug=True)

