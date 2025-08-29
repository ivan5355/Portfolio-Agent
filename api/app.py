import dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  
from openai import OpenAI
import os
from . import prompts

dotenv.load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes. CORS is a security feature that allows or denies requests from different origins.
# This is necessary for the frontend to make requests to the backend.
CORS(app)  

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

    # Create the messages for the OpenAI API.
    # The system message is the system prompt, which is the prompt that the AI will use to generate the response.
    # The user message is the question that the user asked.
    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    response = client.chat.completions.create(  
        max_tokens=500,
        model="gpt-4o-mini",
        messages=messages  
    )

    return jsonify({"answer": response.choices[0].message.content})  

if __name__ == "__main__":
    port = int(os.getenv("PORT", 9000))  
    app.run(debug=True, port=port)