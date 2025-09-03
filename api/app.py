import dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  
from openai import OpenAI
import os
import tiktoken
import dotenv
from flask_limiter import Limiter
from prompts import SYSTEM_PROMPT, CLASSIFIER_PROMPT, UNRELATED_REPLY

dotenv.load_dotenv()

app = Flask(__name__)

CORS(app)

def _get_client_ip():
    
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        first_ip = xff.split(",")[0].strip()
        if first_ip:
            return first_ip
    return request.remote_addr


limiter = Limiter(
    key_func=_get_client_ip,
    app=app,
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
)

# Global variable to store the OpenAI client (lazy initialization)
client = None

# Maximum allowed input tokens for the model
MAX_INPUT_TOKENS = 1000

# JSON handler for 429 Too Many Requests
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"answer": "rate limit exceeded try again tomorrow"}), 200

@app.route("/")
def index():
    return "Hello, World!"

@app.route("/ask", methods=["POST"])
@limiter.limit("5 per 12 hours", methods=["POST"])
def ask():
  
    try:
        # Get the OpenAI client (will initialize if needed)
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        data = request.json
        question = data.get("question")

        if not question:
            return jsonify({"error": "Question is required"}), 400

        # Check token count using tiktoken
        try:
            enc = tiktoken.encoding_for_model("gpt-4o-mini")
        except Exception:
            # Fallback to a common encoding if model-specific encoding is unavailable
            enc = tiktoken.get_encoding("cl100k_base")

        question_tokens = len(enc.encode(question))
        print(f"Question tokens: {question_tokens}")

        # If the question is too long, return a message
        if question_tokens > MAX_INPUT_TOKENS:
            return jsonify({
                "answer": "Question is too long. Please ask a shorter question."
            })

        # First, classify whether the question is related to Ivan's profile
        classification_messages = [
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": question},
        ]

        classification_response = openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=classification_messages,
        )
        label = (classification_response.choices[0].message.content or "").strip().upper()
        
        if label.startswith("UNRELATED"):
                return jsonify({"answer": UNRELATED_REPLY})
        else:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]

            response = openai_client.chat.completions.create(
                model="gpt-5-nano",
                messages=messages,
            )
            
            return jsonify({"answer": response.choices[0].message.content})  
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9000))  
    app.run(debug=True, port=port)
