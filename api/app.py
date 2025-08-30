import dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  
from openai import OpenAI
import os
from prompts import SYSTEM_PROMPT, CLASSIFIER_PROMPT, UNRELATED_REPLY

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

@app.route("/")
def index():
    return "Hello, World!"


@app.route("/ask", methods=["POST"])
def ask():

    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question is required"}), 400

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