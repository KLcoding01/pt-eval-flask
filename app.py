from flask import Flask, render_template, request
import openai
import os

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")  # Store your key in a .env file, never in code!
MODEL = "gpt-4o-mini"

# Template dictionary if you want to expand in the future
TEMPLATES = {
    "LBP Eval Template": "Your long template here...",
    # Add other templates here
}

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    fields = {}

    if request.method == "POST":
        # Capture all submitted fields
        fields = {k: v for k, v in request.form.items()}
        # You can add OpenAI or PT logic here later!
        result = "Form submitted! (This is where you process/save/generate content.)"

    return render_template("index.html")
        templates=TEMPLATES,
        selected_template=fields.get("template", "LBP Eval Template"),
        fields=fields,
        result=result,
    )

# If you want to generate summaries with OpenAI (AJAX or another form)
@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    prompt = request.form.get("summary_prompt", "")
    if not prompt:
        return "No prompt", 400
    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        out = resp["choices"][0]["message"]["content"]
        return out
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(debug=True)
