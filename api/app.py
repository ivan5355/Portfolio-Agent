import dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  
from openai import OpenAI
import os
from prompts import SYSTEM_PROMPT, CLASSIFIER_PROMPT, UNRELATED_REPLY
import tiktoken

dotenv.load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes. CORS is a security feature that allows or denies requests from different origins.
# This is necessary for the frontend to make requests to the backend.
CORS(app)  

# Global variable to store the OpenAI client (lazy initialization)
client = None

def get_openai_client():
    """Get or create OpenAI client with lazy initialization"""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client

# Maximum allowed input tokens for the model
MAX_INPUT_TOKENS = 1000

@app.route("/")
def index():
    return "Hello, World!"

@app.route("/ask", methods=["POST"])
def ask():
    try:
        # Get the OpenAI client (will initialize if needed)
        openai_client = get_openai_client()
        
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
                model="gpt-4o-mini",
                messages=messages,
            )
            
            return jsonify({"answer": response.choices[0].message.content})  
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9000))  
    app.run(debug=True, port=port)
