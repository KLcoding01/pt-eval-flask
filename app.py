from flask import Flask, render_template, request
import openai
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    prompt = request.form.get("prompt")
    if not prompt:
        return render_template("index.html", result="Prompt is required.", prompt=prompt)

    openai.api_key = os.getenv("OPENAI_API_KEY")
    MODEL = "gpt-4o-mini"

    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        result = response["choices"][0]["message"]["content"]
        return render_template("index.html", result=result, prompt=prompt)
    except Exception as e:
        return render_template("index.html", result=f"Error: {e}", prompt=prompt)

if __name__ == "__main__":
    app.run(debug=True)
