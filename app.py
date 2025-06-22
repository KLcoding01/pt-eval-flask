from flask import Flask
import openai
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "PT Eval App is Live!"

openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"

if __name__ == "__main__":
    app.run()
    
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    prompt = request.form.get("prompt")
    if not prompt:
        return "Prompt is required", 400

    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        result = response["choices"][0]["message"]["content"]
        return f"<h2>Generated Output:</h2><pre>{result}</pre><a href='/'>Back</a>"
    except Exception as e:
        return f"Error: {e}", 500
        




TEMPLATES = {
    "LBP Eval Template": """
Medical Diagnosis:
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
""",
}

class PTEvaluationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PT Eval Builder")
        self.geometry("970x900")
        self._build_gui()

    def _build_gui(self):
        bar = ttk.Frame(self); bar.pack(fill="x", padx=8, pady=6)
        ttk.Label(bar, text="Template:").pack(side="left")
        self.template_var = tk.StringVar()
        self.template_cb = ttk.Combobox(
            bar, textvariable=self.template_var, values=list(TEMPLATES.keys()),
            state="readonly", width=40
        )
        self.template_cb.pack(side="left", padx=(4,0))
        if TEMPLATES: self.template_cb.current(0)
        ttk.Button(bar, text="Load", command=self.load_template).pack(side="left", padx=4)
        ttk.Button(bar, text="Load Template (.docx)", command=self.load_docx_template).pack(side="left", padx=4)
        ttk.Button(bar, text="Save As Template", command=self.save_as_template).pack(side="left", padx=4)

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=8, pady=(0,8))

        frm_pt = ttk.Frame(nb); nb.add(frm_pt, text="Patient Info")
        self.name_var   = tk.StringVar()
        self.gender_var = tk.StringVar(value="Female")
        self.dob_var    = tk.StringVar()
        self.age_var    = tk.StringVar()
        self.today_var  = tk.StringVar(value=date.today().strftime("%m-%d-%Y"))

        def calc_age(*_):
            try:
                dob = datetime.strptime(self.dob_var.get(), "%m/%d/%Y").date()
                today = date.today()
                years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                self.age_var.set(str(years))
            except:
                self.age_var.set("")
        self.dob_var.trace_add('write', calc_age)
        ttk.Label(frm_pt, text="Patient Name:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(frm_pt, textvariable=self.name_var).grid(row=0, column=1, sticky="we", padx=4)
        ttk.Label(frm_pt, text="Gender:").grid(row=0, column=2, sticky="e", padx=4)
        gender_cb = ttk.Combobox(frm_pt, textvariable=self.gender_var, values=["Female","Male"], state="readonly", width=8)
        gender_cb.grid(row=0, column=3, padx=4, sticky="w")
        ttk.Label(frm_pt, text="DOB (MM/DD/YYYY):").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(frm_pt, textvariable=self.dob_var).grid(row=1, column=1, sticky="we", padx=4)
        ttk.Label(frm_pt, text="Age:").grid(row=1, column=2, sticky="e", padx=4)
        ttk.Label(frm_pt, textvariable=self.age_var).grid(row=1, column=3, sticky="w")
        ttk.Label(frm_pt, text="Current Date:").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        ttk.Label(frm_pt, textvariable=self.today_var).grid(row=2, column=1, sticky="w")
        for c in range(4): frm_pt.columnconfigure(c, weight=1)

        # ---- HISTORY ----
        frm_hist = ttk.Frame(nb); nb.add(frm_hist, text="History")
        self.med_diag_txt = self._add_section(frm_hist, "Medical Diagnosis:",   0, height=2)
        self.med_hist_txt = self._add_section(frm_hist, "Medical History/HNP:", 1, height=2)
        self.subj_txt     = self._add_section(frm_hist, "Subjective (HPI):",    2, height=4)
        self.meds_txt     = self._add_section(frm_hist, "Current Medication(s):",3, height=2)
        self.tests_txt    = self._add_section(frm_hist, "Diagnostic Test(s):",   4, height=2)
        self.dme_txt      = self._add_section(frm_hist, "DME/Assistive Device:", 5, height=2)
        self.plof_txt     = self._add_section(frm_hist, "PLOF:",                 6, height=2)

        # ---- PAIN ----
        frm_pain = ttk.Frame(nb); nb.add(frm_pain, text="Pain")
        pain_labels = [
            "Area/Location of Injury",
            "Onset/Exacerbation Date",
            "Condition of Injury",
            "Mechanism of Injury",
            "Pain Rating (P/B/W)",
            "Pain Frequency",
            "Description",
            "Aggravating Factor",
            "Relieved By",
            "Interferes With",
        ]
        self.pain_vars = {}
        for i, lbl in enumerate(pain_labels):
            ttk.Label(frm_pain, text=f"{lbl}:").grid(row=i, column=0, sticky="e", pady=2)
            var = tk.StringVar()
            ttk.Entry(frm_pain, textvariable=var).grid(row=i, column=1, sticky="we", pady=2)
            key = lbl.lower().replace("/", "").replace("(", "").replace(")", "").replace(" ", "_").replace("-", "_")
            self.pain_vars[key] = var
        frm_pain.columnconfigure(1, weight=1)

        # ---- OBJECTIVE ----
        frm_obj = ttk.Frame(nb); nb.add(frm_obj, text="Objective")
        self.posture_txt   = self._add_section(frm_obj, "Posture:",                     0, height=2)
        self.rom_txt       = self._add_section(frm_obj, "ROM:",                         1, height=3)
        self.str_txt       = self._add_section(frm_obj, "Muscle Strength Test:",        2, height=2)
        self.palpation_txt = self._add_section(frm_obj, "Palpation:",                   3, height=2)
        self.func_txt      = self._add_section(frm_obj, "Functional Test(s):",          4, height=2)
        self.special_txt   = self._add_section(frm_obj, "Special Test(s):",             5, height=2)
        self.impair_txt    = self._add_section(frm_obj, "Current Functional Mobility Impairment(s):", 6, height=3)

        # ---- DiFF DX ----
        frm_diff = ttk.Frame(nb); nb.add(frm_diff, text="Diff Dx")
        ttk.Label(frm_diff, text="Best-Fit Diagnosis:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.diff_txt = scrolledtext.ScrolledText(frm_diff, wrap="word", height=6)
        self.diff_txt.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        frm_diff.columnconfigure(0, weight=1); frm_diff.rowconfigure(1, weight=1)

        # ---- ASSESSMENT SUMMARY ----
        frm_sum = ttk.Frame(nb); nb.add(frm_sum, text="Assessment Summary")
        ttk.Label(frm_sum, text="Assessment Summary:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.summary_txt = scrolledtext.ScrolledText(frm_sum, wrap="word", height=8)
        self.summary_txt.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        frm_sum.columnconfigure(0, weight=1); frm_sum.rowconfigure(1, weight=1)

        # ---- PLAN ----
        frm_plan = ttk.Frame(nb); nb.add(frm_plan, text="Plan")
        self.goals_txt   = self._add_section(frm_plan, "Goals:",        0, height=4)
        self.freq_txt    = self._add_section(frm_plan, "Frequency/Duration:",    1, height=1)
        self.interv_txt  = self._add_section(frm_plan, "Intervention:", 2, height=3)
        self.proc_txt    = self._add_section(frm_plan, "Treatment Procedures:", 3, height=4)
        frm_plan.columnconfigure(1, weight=1)

        btns = ttk.Frame(self); btns.pack(fill="x", padx=8, pady=6)
        for txt, cmd in [
            ("Dictate",     self.capture_dictation),
            ("Diff Dx",     self.generate_diff_dx),
            ("Gen Summary", self.generate_assess_summary),
            ("Gen Goals",   self.generate_goals),
            ("To Template", self.transfer_to_template),
            ("Save .docx",  self.save_to_word),
        ]:
            ttk.Button(btns, text=txt, command=cmd).pack(side="left", expand=True, fill="x", padx=4)

    def _add_section(self, parent, title, row, height=3):
        ttk.Label(parent, text=title).grid(row=row, column=0, sticky="nw", pady=2)
        txt = scrolledtext.ScrolledText(parent, wrap="word", height=height)
        txt.grid(row=row, column=1, sticky="nsew", padx=4, pady=2)
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(1, weight=1)
        return txt

    def load_template(self):
        template = TEMPLATES[self.template_var.get()].strip().splitlines()
        for txt in (
            self.med_diag_txt, self.med_hist_txt, self.subj_txt,
            self.meds_txt, self.tests_txt, self.dme_txt, self.plof_txt,
            self.posture_txt, self.rom_txt, self.str_txt,
            self.palpation_txt, self.func_txt, self.special_txt, self.impair_txt,
            self.goals_txt, self.freq_txt, self.interv_txt, self.proc_txt
        ):
            txt.delete("1.0", "end")
        for var in self.pain_vars.values():
            var.set("")
        text_blocks = {
            "Medical Diagnosis": self.med_diag_txt,
            "Medical History/HNP": self.med_hist_txt,
            "Subjective": self.subj_txt,
            "Current Medication(s)": self.meds_txt,
            "Diagnostic Test(s)": self.tests_txt,
            "DME/Assistive Device": self.dme_txt,
            "PLOF": self.plof_txt,
            "Posture": self.posture_txt,
            "ROM": self.rom_txt,
            "Muscle Strength Test": self.str_txt,
            "Palpation": self.palpation_txt,
            "Functional Test(s)": self.func_txt,
            "Special Test(s)": self.special_txt,
            "Current Functional Mobility Impairment(s)": self.impair_txt,
            "Goals": self.goals_txt,
            "Frequency/Duration": self.freq_txt,
            "Intervention": self.interv_txt,
            "Treatment Procedures": self.proc_txt,
        }
        buf = []
        key = None
        for line in template:
            line = line.strip()
            if not line:
                continue
            for field in text_blocks:
                if line.startswith(field + ":"):
                    if key and buf:
                        text_blocks[key].insert("1.0", "\n".join(buf))
                    key = field
                    buf = []
                    after = line[len(field)+1:].strip()
                    if after:
                        buf.append(after)
                    break
            else:
                pain_fields = [
                    "Area/Location of Injury",
                    "Onset/Exacerbation Date",
                    "Condition of Injury",
                    "Mechanism of Injury",
                    "Pain Rating (P/B/W)",
                    "Pain Frequency",
                    "Description",
                    "Aggravating Factor",
                    "Relieved By",
                    "Interferes With",
                ]
                for pf in pain_fields:
                    if line.startswith(pf + ":"):
                        val = line.split(":", 1)[1].strip()
                        pf_key = pf.lower().replace("/", "").replace("(", "").replace(")", "").replace(" ", "_").replace("-", "_")
                        if pf_key in self.pain_vars:
                            self.pain_vars[pf_key].set(val)
                        break
                else:
                    if key:
                        buf.append(line)
        if key and buf:
            text_blocks[key].insert("1.0", "\n".join(buf))
        messagebox.showinfo("Loaded", "Embedded text template loaded successfully.")

    def load_docx_template(self):
        from tkinter import filedialog, messagebox
        from docx import Document

        path = filedialog.askopenfilename(
            filetypes=[("Word Documents", "*.docx")],
            title="Select a PT Eval .docx template"
        )
        if not path:
            return

        try:
            doc = Document(path)
            doc_text = "\n".join([p.text for p in doc.paragraphs])

            def extract_section(header, text, stop_headers):
                start = text.find(header)
                if start == -1:
                    return ""
                start += len(header)
                stop = len(text)
                for sh in stop_headers:
                    idx = text.find(sh, start)
                    if idx != -1 and idx < stop:
                        stop = idx
                return text[start:stop].strip()

            structure = [
                ("Medical Diagnosis:",      self.med_diag_txt),
                ("Medical History/HNP:",    self.med_hist_txt),
                ("Subjective:",             self.subj_txt),
                ("Pain:",                   None),
                ("Objective:",              None),
                ("Assessment Summary:",     self.summary_txt),
                ("Goals:",                  self.goals_txt),
                ("Frequency:",              self.freq_txt),
                ("Intervention:",           self.interv_txt),
            ]
            for i, (header, widget) in enumerate(structure):
                stop_headers = [h for h, _ in structure[i+1:]]
                value = extract_section(header, doc_text, stop_headers)
                if widget is not None:
                    widget.delete("1.0", "end")
                    widget.insert("1.0", value)

            pain_section = extract_section("Pain:", doc_text, ["Objective:"])
            pain_map = {
                "Area/Location of Injury:": "arealocation_of_injury",
                "Onset/Exacerbation Date:": "onsetexacerbation_date",
                "Condition of Injury:":     "condition_of_injury",
                "Mechanism of Injury:":     "mechanism_of_injury",
                "Pain Rating":              "pain_rating_pbw",
                "Frequency:":               "pain_frequency",
                "Description:":             "description",
                "Aggravating Factor:":      "aggravating_factor",
                "Relieved By:":             "relieved_by",
                "Interferes With:":         "interferes_with",
            }
            for line in pain_section.splitlines():
                for label, key in pain_map.items():
                    if line.strip().startswith(label):
                        self.pain_vars[key].set(line.split(":", 1)[-1].strip())
                        break
            def fill_subfield(label, widget):
                idx = pain_section.find(label)
                if idx != -1:
                    after = pain_section[idx+len(label):].split("\n", 1)[0]
                    widget.delete("1.0", "end")
                    widget.insert("1.0", after.strip())
            fill_subfield("Current Medication(s):", self.meds_txt)
            fill_subfield("Diagnostic Test(s):", self.tests_txt)
            fill_subfield("DME/Assistive Device:", self.dme_txt)
            fill_subfield("PLOF:", self.plof_txt)

            obj_section = extract_section("Objective:", doc_text, ["Assessment Summary:", "Goals:"])
            obj_map = [
                ("Posture:",       self.posture_txt),
                ("ROM:",           self.rom_txt),
                ("Muscle Strength Test:", self.str_txt),
                ("Palpation:",     self.palpation_txt),
                ("Functional Test(s):", self.func_txt),
                ("Special Test(s):", self.special_txt),
                ("Current Functional Mobility Impairment(s):", self.impair_txt),
            ]
            for i, (label, widget) in enumerate(obj_map):
                stop_labels = [lbl for lbl, _ in obj_map[i+1:]]
                val = extract_section(label, obj_section, stop_labels)
                widget.delete("1.0", "end")
                widget.insert("1.0", val)

            messagebox.showinfo("Loaded", "Template loaded from .docx!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load template:\n{e}")

    def save_as_template(self):
        from docx import Document
        doc = Document()

        def add_section(title, content):
            doc.add_paragraph(title)
            doc.add_paragraph(content.strip() if content.strip() else "")

        add_section("Medical Diagnosis:", self.med_diag_txt.get("1.0", "end"))
        add_section("Medical History/HNP:", self.med_hist_txt.get("1.0", "end"))
        add_section("Subjective:", self.subj_txt.get("1.0", "end"))
        pain_lines = [
            f"Area/Location of Injury: {self.pain_vars['arealocation_of_injury'].get()}",
            f"Onset/Exacerbation Date: {self.pain_vars['onsetexacerbation_date'].get()}",
            f"Condition of Injury: {self.pain_vars['condition_of_injury'].get()}",
            f"Mechanism of Injury: {self.pain_vars['mechanism_of_injury'].get()}",
            f"Pain Rating (Present/Best/Worst): {self.pain_vars['pain_rating_pbw'].get()}",
            f"Frequency: {self.pain_vars['pain_frequency'].get()}",
            f"Description: {self.pain_vars['description'].get()}",
            f"Aggravating Factor: {self.pain_vars['aggravating_factor'].get()}",
            f"Relieved By: {self.pain_vars['relieved_by'].get()}",
            f"Interferes With: {self.pain_vars['interferes_with'].get()}",
            "",
            f"Current Medication(s): {self.meds_txt.get('1.0', 'end').strip()}",
            f"Diagnostic Test(s): {self.tests_txt.get('1.0', 'end').strip()}",
            f"DME/Assistive Device: {self.dme_txt.get('1.0', 'end').strip()}",
            f"PLOF: {self.plof_txt.get('1.0', 'end').strip()}",
        ]
        add_section("Pain:", "\n".join(pain_lines))
        obj_lines = [
            f"Posture: {self.posture_txt.get('1.0', 'end').strip()}",
            "",
            f"ROM: \n{self.rom_txt.get('1.0', 'end').strip()}",
            "",
            f"Muscle Strength Test: \n{self.str_txt.get('1.0', 'end').strip()}",
            "",
            f"Palpation: \n{self.palpation_txt.get('1.0', 'end').strip()}",
            "",
            f"Functional Test(s): \n{self.func_txt.get('1.0', 'end').strip()}",
            "",
            f"Special Test(s): \n{self.special_txt.get('1.0', 'end').strip()}",
            "",
            f"Current Functional Mobility Impairment(s): \n{self.impair_txt.get('1.0', 'end').strip()}",
        ]
        add_section("Objective:", "\n".join(obj_lines))
        add_section("Assessment Summary:", self.summary_txt.get("1.0", "end"))
        add_section("Goals:", self.goals_txt.get("1.0", "end"))
        add_section("Frequency:", self.freq_txt.get("1.0", "end"))
        add_section("Intervention:", self.interv_txt.get("1.0", "end"))
        add_section("Treatment Procedures:", self.proc_txt.get("1.0", "end"))

        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Documents", "*.docx")],
            initialfile="Template_From_GUI.docx"
        )
        if path:
            doc.save(path)
            messagebox.showinfo("Template Saved", f"Template saved as:\n{path}")

    def capture_dictation(self):
        messagebox.showinfo("Dictation", "Coming soon…")

    def generate_diff_dx(self):
        hpi  = self.subj_txt.get("1.0","end").strip()
        pain = "; ".join(f"{k}: {v.get()}" for k,v in self.pain_vars.items())
        obj  = "\n".join([
            f"Posture: {self.posture_txt.get('1.0','end').strip()}",
            f"ROM: {self.rom_txt.get('1.0','end').strip()}",
            f"Strength: {self.str_txt.get('1.0','end').strip()}",
        ])
        prompt = (
            "You are a PT clinical assistant. Provide the single best-fit diagnosis:\n\n"
            f"Subjective:\n{hpi}\n\nPain:\n{pain}\n\nObjective:\n{obj}"
        )
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"user","content":prompt}]
            )
            out = resp.choices[0].message.content.strip()
            self.diff_txt.delete("1.0","end")
            self.diff_txt.insert("1.0", out)
        except Exception as e:
            messagebox.showerror("OpenAI Error", str(e))

    def generate_assess_summary(self):
        name   = self.name_var.get()
        gender = self.gender_var.get()
        dob    = self.dob_var.get()
        age    = self.age_var.get()
        today  = self.today_var.get()
        pmh    = self.med_hist_txt.get("1.0","end").strip()
        dx     = self.diff_txt.get("1.0","end").strip()
        subj   = self.subj_txt.get("1.0","end").strip()
        impair = self.impair_txt.get("1.0","end").strip()
        func   = self.func_txt.get("1.0","end").strip()
        rom    = self.rom_txt.get("1.0","end").strip()
        strg   = self.str_txt.get("1.0","end").strip()
        prefix = "Pt"  # Always use "Pt"
        prompt = f"""
Generate a concise, 7-8 sentence Physical Therapy assessment summary for PT documentation. Use clinical, professional language and use abbreviations only (e.g., use HEP, ADLs, LBP, STM, TherEx, etc.—do not spell out the abbreviation and do not write both full term and abbreviation). Never use the phrase 'The patient'; instead, use 'Pt' at the start of each relevant sentence. Start with: "{prefix} {name}, a {age} y/o {gender.lower()} with relevant history of {pmh}." 
Include: 
1) How/when/why pt was seen (PT initial eval on {today} for {subj}), 
2) mechanism of injury if available,
3) main differential dx ({dx}),
4) current impairments (strength: {strg}; ROM: {rom}; balance/mobility: {impair}), 
5) functional/activity/participation limitations: {func},
6) a professional prognosis and 
7) that skilled PT will help pt return to PLOF.
Do not use bulleted or numbered lists—just a single, well-written summary paragraph.
"""
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"user","content":prompt}]
            )
            out = resp.choices[0].message.content.strip()
            self.summary_txt.delete("1.0","end")
            self.summary_txt.insert("1.0", out)
        except Exception as e:
            messagebox.showerror("OpenAI Error", str(e))

    def generate_goals(self):
        summary = self.summary_txt.get("1.0", "end").strip()
        dx      = self.diff_txt.get("1.0", "end").strip()
        impair  = self.impair_txt.get("1.0", "end").strip()
        func    = self.func_txt.get("1.0", "end").strip()

        prompt = f"""
You are a clinical assistant helping a PT write documentation. Using the following information, generate short-term and long-term PT goals in the EXACT format and language as below, but adapt the content based on the findings and summary from this evaluation.

EVALUATION DATA:
Assessment Summary: {summary}
Diagnosis: {dx}
Impairments: {impair}
Functional Limitations: {func}

USE THIS FORMAT EXACTLY FOR YOUR RESPONSE (adapt the content as needed):

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
        """

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            out = resp.choices[0].message.content.strip()
            self.goals_txt.delete("1.0", "end")
            self.goals_txt.insert("1.0", out)
        except Exception as e:
            messagebox.showerror("OpenAI Error", str(e))

    def transfer_to_template(self):
        from docx import Document

        doc = Document()

        def add_section(title, content, add_sep=True):
            doc.add_paragraph(f"{title}")
            if content.strip():
                doc.add_paragraph(content.strip())
            else:
                doc.add_paragraph("")  # empty line if no content
            if add_sep:
                doc.add_paragraph("-" * 114)

        # --- Section 1: Medical Diagnosis ---
        add_section("Medical Diagnosis:", self.med_diag_txt.get("1.0", "end"), add_sep=True)
        add_section("Medical History/HNP:", self.med_hist_txt.get("1.0", "end"), add_sep=True)
        add_section("Subjective:", self.subj_txt.get("1.0", "end"), add_sep=True)

        pain_lines = [
            f"Area/Location of Injury: {self.pain_vars['arealocation_of_injury'].get()}",
            f"Onset/Exacerbation Date: {self.pain_vars['onsetexacerbation_date'].get()}",
            f"Condition of Injury: {self.pain_vars['condition_of_injury'].get()}",
            f"Mechanism of Injury: {self.pain_vars['mechanism_of_injury'].get()}",
            f"Pain Rating (Present/Best/Worst): {self.pain_vars['pain_rating_pbw'].get()}",
            f"Frequency: {self.pain_vars['pain_frequency'].get()}",
            f"Description: {self.pain_vars['description'].get()}",
            f"Aggravating Factor: {self.pain_vars['aggravating_factor'].get()}",
            f"Relieved By: {self.pain_vars['relieved_by'].get()}",
            f"Interferes With: {self.pain_vars['interferes_with'].get()}",
            "",
            f"Current Medication(s): {self.meds_txt.get('1.0', 'end').strip()}",
            f"Diagnostic Test(s): {self.tests_txt.get('1.0', 'end').strip()}",
            f"DME/Assistive Device: {self.dme_txt.get('1.0', 'end').strip()}",
            f"PLOF: {self.plof_txt.get('1.0', 'end').strip()}",
        ]
        add_section("Pain:", "\n".join(pain_lines), add_sep=True)

        obj_lines = [
            f"Posture: {self.posture_txt.get('1.0', 'end').strip()}",
            "",
            f"ROM: \n{self.rom_txt.get('1.0', 'end').strip()}",
            "",
            f"Muscle Strength Test: \n{self.str_txt.get('1.0', 'end').strip()}",
            "",
            f"Palpation: \n{self.palpation_txt.get('1.0', 'end').strip()}",
            "",
            f"Functional Test(s): \n{self.func_txt.get('1.0', 'end').strip()}",
            "",
            f"Special Test(s): \n{self.special_txt.get('1.0', 'end').strip()}",
            "",
            f"Current Functional Mobility Impairment(s): \n{self.impair_txt.get('1.0', 'end').strip()}",
        ]
        add_section("Objective:", "\n".join(obj_lines), add_sep=False)

        doc.add_paragraph("Assessment Summary: ")
        doc.add_paragraph(self.summary_txt.get("1.0", "end").strip())
        doc.add_paragraph("-" * 114)

        doc.add_paragraph("Goals: ")
        doc.add_paragraph(self.goals_txt.get("1.0", "end").strip())
        doc.add_paragraph("-" * 114)

        freq = self.freq_txt.get("1.0", "end").strip()
        doc.add_paragraph(f"Frequency: {freq if freq else ''}")

        intervention = self.interv_txt.get("1.0", "end").strip()
        doc.add_paragraph(f"Intervention: {intervention if intervention else ''}")
        doc.add_paragraph("-" * 114)

        doc.add_paragraph(self.proc_txt.get("1.0", "end").strip())

        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Documents", "*.docx")],
            initialfile="PT_Eval.docx"
        )
        if path:
            doc.save(path)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")
        else:
            messagebox.showwarning("Save Cancelled", "No file was saved.")

    def save_to_word(self):
        self.transfer_to_template()

if __name__ == "__main__":
    app.run(debug=True)
