from flask import Flask, render_template, request, send_file
import os
import io
from docx import Document

app = Flask(__name__)

TEMPLATES = { "LBP Eval Template": """(your long template above)""" }

@app.route("/", methods=["GET", "POST"])
def index():
    fields = {}
    result = ""
    if request.method == "POST":
        # Get all fields from the web form
        fields = {k: v for k, v in request.form.items()}
        action = request.form.get("action", "save")
        if action == "save_template":
            # Save as docx
            doc = Document()
            for k, v in fields.items():
                doc.add_paragraph(f"{k}: {v}")
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            return send_file(buf, as_attachment=True, download_name="PT_Eval.docx")
        elif action == "load":
            # Load the template (fill all fields)
            # Parse your template and set to fields
            pass
        result = "Form submitted!"
    return render_template(
        "index.html",
        templates=TEMPLATES,
        selected_template=fields.get("template", "LBP Eval Template"),
        fields=fields,
        result=result,
    )

if __name__ == "__main__":
    app.run(debug=True)
