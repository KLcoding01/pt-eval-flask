# soap.py

def generate_soap(fields):
    """
    Generate a PT SOAP note summary from eval builder fields.
    """
    s = []
    s.append("S: " + (fields.get('subjective', '').strip() or 'No subjective findings noted.'))
    # Compose Objective from individual fields if 'objective' field is empty
    objective = fields.get('objective', '').strip()
    if not objective:
        obj_parts = [fields.get(k, '').strip() for k in [
            'posture', 'rom', 'strength', 'palpation', 'functional', 'special', 'impairments'
        ] if fields.get(k, '').strip()]
        objective = "; ".join(obj_parts)
    s.append("O: " + (objective or 'No objective findings noted.'))
    s.append("A: " + (fields.get('summary', '').strip() or 'No assessment/summary provided.'))
    # Plan: Use 'goals', 'plan', or 'intervention' in order of preference
    plan = fields.get('goals', '').strip() or fields.get('plan', '').strip() or fields.get('intervention', '').strip()
    s.append("P: " + (plan or 'No plan provided.'))
    return "\n".join(s)

def generate_daily_note(fields):
    """
    Generate a Daily SOAP note from daily note fields.
    """
    lines = []
    lines.append(f"Patient: {fields.get('name','')} | Date: {fields.get('currentdate','') or fields.get('date','')}")
    lines.append("Subjective: " + (fields.get('subjective','').strip() or 'N/A'))
    lines.append("Objective: " + (fields.get('objective','').strip() or 'N/A'))
    lines.append("Assessment: " + (fields.get('summary','').strip() or fields.get('assessment','').strip() or 'N/A'))
    lines.append("Plan: " + (fields.get('plan','').strip() or 'N/A'))
    return "\n".join(lines)
