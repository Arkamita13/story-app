import os
import time
from flask import Flask, request, jsonify, render_template_string
from google import genai

app = Flask(__name__)

# Render-এর Environment Variable থেকে কী নেওয়া হচ্ছে
API_KEY = os.environ.get("GEMINI_API_KEY")

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Story Creator</title>
  <style>
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
      max-width: 640px; 
      margin: 30px auto; 
      padding: 0 16px; 
      background-color: #f9fafb; 
      color: #1f2937; 
    }
    h1 { text-align: center; color: #111827; }
    .card { 
      background: #ffffff; 
      padding: 24px; 
      border-radius: 12px; 
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); 
    }
    label { font-weight: 600; display: block; margin-top: 14px; margin-bottom: 6px; }
    select, textarea, button { 
      width: 100%; 
      padding: 10px; 
      border: 1px solid #d1d5db; 
      border-radius: 6px; 
      box-sizing: border-box; 
      font-size: 15px; 
    }
    button { 
      margin-top: 18px; 
      background-color: #2563eb; 
      color: #ffffff; 
      border: none; 
      font-weight: 600; 
      cursor: pointer; 
      padding: 12px; 
      border-radius: 6px; 
    }
    button:hover { background-color: #1d4ed8; }
    button:disabled { background-color: #9ca3af; cursor: not-allowed; }
    #output { 
      margin-top: 20px; 
      padding: 16px; 
      background: #f3f4f6; 
      border-radius: 8px; 
      white-space: pre-wrap; 
      line-height: 1.6; 
      display: none; 
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>📖 AI Story Generator</h1>
    <p style="text-align:center; color:#6b7280; margin-top:-8px;">Powered by Google Gemini</p>

    <label for="genre">Genre</label>
    <select id="genre">
      <option>Fantasy</option>
      <option>Sci-Fi</option>
      <option>Mystery</option>
      <option>Romance</option>
      <option>Adventure</option>
      <option>Comedy</option>
      <option>Drama</option>
    </select>

    <label for="outline">Story Outline</label>
    <textarea id="outline" rows="5" placeholder="Write your plot or story outline here..."></textarea>

    <button id="generateBtn" onclick="generateStory()">Create Story</button>

    <div id="output"></div>
  </div>

  <script>
    async function generateStory() {
      const genre = document.getElementById("genre").value;
      const outline = document.getElementById("outline").value.trim();
      const output = document.getElementById("output");
      const btn = document.getElementById("generateBtn");

      if (!outline) {
        alert("Please enter a story outline first.");
        return;
      }

      btn.disabled = true;
      btn.innerText = "Writing story with Gemini...";
      output.style.display = "block";
      output.innerText = "Generating story, please wait...";

      try {
        const response = await fetch("/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ genre, outline })
        });
        const data = await response.json();
        if (data.error) {
          output.innerText = "Error: " + data.error;
        } else {
          output.innerText = data.story;
        }
      } catch (err) {
        output.innerText = "Network error: " + err.message;
      } finally {
        btn.disabled = false;
        btn.innerText = "Create Story";
      }
    }
  </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

@app.route("/generate", methods=["POST"])
def generate():
    if not API_KEY:
        return jsonify({"error": "GEMINI_API_KEY environment variable is not set on Render."}), 500

    data = request.get_json() or {}
    genre = data.get("genre", "General")
    outline = data.get("outline", "")

    prompt = f"Write an engaging, complete, and creative story in the {genre} genre based on this outline:\n\n{outline}"

    client = genai.Client(api_key=API_KEY)

    # সব ভ্যালিড মডেলের তালিকা (একটায় সমস্যা হলে পরেরটা ট্রাই করবে)
    candidate_models = [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-pro-latest"
    ]

    errors = []
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    return jsonify({"story": response.text})
            except Exception as e:
                err_str = str(e)
                errors.append(f"{model_name}: {err_str}")
                if "503" in err_str:
                    time.sleep(2)  # লোড বেশি থাকলে ২ সেকেন্ড বিরতি দিয়ে আবার চেষ্টা করবে
                    continue
                break  # 404 হলে সাথে সাথে পরের মডেলে চলে যাবে

    return jsonify({"error": "All available models failed: " + " | ".join(errors[:2])}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
