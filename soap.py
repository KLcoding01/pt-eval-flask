import os
import re
import random
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

REPLACEMENTS = {
    "gme": "Give me 6 sentences summary for PT tx utilizing manual therapy, stretching, TherEx, TherAct, good tolerance, decrease stiffness/tenderness, progressing with tx focusing on",
    "gpoc": "Give me 1 sentence PT POC for STM, TherEx, TherAct to address pain, weakness, and re-integrate to ADLs.",
    "1tx": "ther-ex, ther-act, manual therapy, stretch, TPRs",
    "1tol": "fair+, reduce tension, improved",
    "1slow": "slowly progressing, some functional improvement, pain reduction",
    "1fair": "fair progression, marked improvement with activity and ther-ex",
    "1good": "good progression, expected to meet goals, good prognosis to meet goals",
    "1poc": "Continue with POC work on improving strength, mobility, flexibility, pain management, ther-ex, ther-act, manual therapy."
}

def replace_terms(text):
    for short, full in REPLACEMENTS.items():
        pattern = r'(?<!\w)' + re.escape(short) + r'(?!\w)'
        text = re.sub(pattern, full, text, flags=re.IGNORECASE)
    return text

def gpt_call(prompt, max_tokens=350, system_msg=None):
    temperature = random.uniform(0.65, 0.85)
    try:
        msgs = []
        if system_msg:
            msgs.append({"role": "system", "content": system_msg})
        msgs.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=MODEL,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI error: {e}"

# ---- SOAP Note tab ----
def generate_soap(fields, use_ai=True):
    """
    Generate a PT SOAP note summary from SOAP note tab fields.
    """
    if use_ai:
        note = (
            f"Dx Summary: {fields.get('dx','')}. "
            f"Interventions: {fields.get('iv','')}. "
            f"Tolerance: {fields.get('tol','')}. "
            f"Progress: {fields.get('prog','')}. "
            f"Plan: {fields.get('plan','')}."
        )
        prompt = (
            "Based on the following PT session details, write a concise 6-sentence paragraph summary. "
            "Avoid 'pt reported', abbreviate 'Patient' to 'Pt', and always mention that Pt needs continued PT. "
            "Use clinical abbreviations (e.g., STM, TherEx, TherAct, LBP), avoid section labels like S:, O:, A:, P:, "
            "and do not include any headers.\n\n"
            f"{replace_terms(note)}"
        )
        system_msg = (
            "You are a licensed physical therapist writing concise, paragraph-style visit summaries using common clinical abbreviations."
        )
        return gpt_call(prompt, max_tokens=500, system_msg=system_msg)
    else:
        s = []
        s.append("Dx Summary: " + (fields.get('dx', '').strip() or ''))
        s.append("Interventions: " + (fields.get('iv', '').strip() or ''))
        s.append("Tolerance: " + (fields.get('tol', '').strip() or ''))
        s.append("Progress: " + (fields.get('prog', '').strip() or ''))
        s.append("Plan: " + (fields.get('plan', '').strip() or ''))
        return "\n".join(s)

# ---- PT Eval tab ----
def generate_eval(fields, use_ai=True):
    """
    Generate a summary from PT Eval tab fields.
    """
    if use_ai:
        prompt = (
            "Summarize this PT evaluation for EMR using clinical abbreviations and a professional tone. "
            "Bullet points are okay for findings. Do not use full patient name, just 'Pt'.\n\n"
            f"Name: {fields.get('name','')}\n"
            f"Diagnosis: {fields.get('meddiag','')}\n"
            f"History: {fields.get('history','')}\n"
        )
        system_msg = "You are a PT summarizing a PT evaluation for EMR."
        return gpt_call(prompt, max_tokens=400, system_msg=system_msg)
    else:
        return (
            f"Name: {fields.get('name','')}\n"
            f"Diagnosis: {fields.get('meddiag','')}\n"
            f"History: {fields.get('history','')}"
        )

# ---- Daily Note tab ----
def generate_daily_note(fields, use_ai=True):
    """
    Generate a summary from Daily Note tab fields.
    """
    if use_ai:
        prompt = (
            "Write a concise daily PT SOAP note summary for the medical record. Use only these fields, "
            "using clinical abbreviations and a professional tone. Avoid headers (S:, O:, A:, P:) and only use info provided:\n\n"
            f"Subjective: {fields.get('subjective','')}\n"
            f"Objective: {fields.get('objective','')}\n"
            f"Assessment: {fields.get('assessment','')}\n"
            f"Plan: {fields.get('plan','')}\n"
        )
        system_msg = "You are a PT writing a daily SOAP progress note."
        return gpt_call(prompt, max_tokens=350, system_msg=system_msg)
    else:
        return (
            f"S: {fields.get('subjective','')}\n"
            f"O: {fields.get('objective','')}\n"
            f"A: {fields.get('assessment','')}\n"
            f"P: {fields.get('plan','')}"
        )

