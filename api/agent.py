import os
import json
from google import genai
from api.prompts import SYSTEM_PROMPT

# Initialize Gemini client once per container using GOOGLE_API_KEY env var
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")


def set_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"


def handler(request, response):
    try:
        # Always attach CORS headers
        set_cors_headers(response)

        # Handle CORS preflight request
        if request.method == "OPTIONS":
            response.status_code = 200
            response.write("")
            return

        # Only allow POST requests
        if request.method != "POST":
            response.status_code = 405
            response.headers["Content-Type"] = "application/json"
            response.write(json.dumps({"error": "Method Not Allowed"}))
            return

        # Parse the request body
        data = {}
        try:
            data = request.json() or {}
        except Exception:
            # Fallback: try to parse raw body if available
            try:
                raw_body = getattr(request, "body", b"{}")
                if isinstance(raw_body, (bytes, bytearray)):
                    raw_body = raw_body.decode("utf-8")
                data = json.loads(raw_body or "{}")
            except Exception:
                data = {}

        prompt = data.get("prompt") if isinstance(data, dict) else None
        if not prompt:
            response.status_code = 400
            response.headers["Content-Type"] = "application/json"
            response.write(json.dumps({"error": "No prompt provided"}))
            return

        # Construct the full prompt
        full_prompt = f"System: {SYSTEM_PROMPT}\nUser: {prompt}\nAssistant:"

        # Call the Gemini API
        result = client.models.generate_content(
            model="gemini-1.5-flash",
            input=full_prompt,
        )

        # Return the response
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response.write(json.dumps({"output": result.text}))

    except Exception as e:
        # Ensure CORS headers on error as well
        set_cors_headers(response)
        response.status_code = 500
        response.headers["Content-Type"] = "application/json"
        response.write(json.dumps({"error": f"Internal server error: {str(e)}"}))
