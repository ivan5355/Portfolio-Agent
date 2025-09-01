import dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  
from openai import OpenAI
import os
from prompts import SYSTEM_PROMPT, CLASSIFIER_PROMPT, UNRELATED_REPLY
import tiktoken
from datetime import datetime, timezone
import threading

dotenv.load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes. CORS is a security feature that allows or denies requests from different origins.
# This is necessary for the frontend to make requests to the backend.
CORS(app)  

# Check if API key is set
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Initialize the OpenAI client. This is used to make requests to the OpenAI API.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Maximum allowed input tokens for the model
MAX_INPUT_TOKENS = 50
DAILY_REQUEST_LIMIT = 5

# In-memory request counter: maps (client_id, YYYY-MM-DD) -> count
request_counts_lock = threading.Lock()
request_counts = {}


def get_client_id():
    """Get the client id by IP address"""

    # Get the IP address from the X-Forwarded-For header
    fwd = request.headers.get("X-Forwarded-For")

    # If the X-Forwarded-For header is not set, use the remote address
    if fwd:
        ip = fwd.split(",")[0].strip()
    else:
        ip = request.remote_addr or "unknown"
    return f"ip:{ip}"

def today_key():
    return datetime.now(timezone.utc).date().isoformat()

def has_exceeded_daily_limit(client_id: str):
    """Return (exceeded, limit, used). Increments usage if not exceeded."""
    key = (client_id, today_key())

    # Get the request count for the client id and today
    with request_counts_lock:

        count = request_counts.get(key, 0)

        # If the request count is greater than the daily request limit, return True
        if count >= DAILY_REQUEST_LIMIT:
            return True, DAILY_REQUEST_LIMIT, count
        request_counts[key] = count + 1

        # Return False, the daily request limit, and the request count
        return False, DAILY_REQUEST_LIMIT, request_counts[key]


@app.route("/")
def index():
    return "Hello, World!"

@app.route("/ask", methods=["POST"])
def ask():

    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    # Enforce daily request limit per IP address
    client_id = get_client_id()
    exceeded, _, _ = has_exceeded_daily_limit(client_id)
    if exceeded:
        return jsonify({
            "answer": f"You've reached the daily limit of {DAILY_REQUEST_LIMIT} requests for your IP. Please try again tomorrow."
        })

    try:
        print("Using model-specific encoding")
        enc = tiktoken.encoding_for_model("gpt-5-nano")
    except Exception:
        print("Using fallback encoding")
        
        # Fallback to a common encoding if model-specific encoding is unavailable
        enc = tiktoken.get_encoding("cl100k_base")

    question_tokens = len(enc.encode(question))
    print(f"Question tokens: {question_tokens}")
    if question_tokens > MAX_INPUT_TOKENS:
        return jsonify({
            "answer": "Question is too long. Please ask a shorter question."
        })

    # First, classify whether the question is related to Ivan's profile
    classification_messages = [
        {"role": "system", "content": CLASSIFIER_PROMPT},
        {"role": "user", "content": question},
    ]

    classification_response = client.chat.completions.create(
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

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages
        )
        
        return jsonify({"answer": response.choices[0].message.content})  


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9000))  
    app.run(debug=True, port=port)