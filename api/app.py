import dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  
from openai import OpenAI
import os
import tiktoken
# Rate limiting setup (IP-based)
from flask_limiter import Limiter

# Ensure CLASSIFIER_PROMPT is defined before any route uses it
CLASSIFIER_PROMPT = (
    "You determine if the user's question is about  skills, certifications, projects, experience, education, awards, or contact info\n"
    "Respond with exactly one word: RELATED or UNRELATED.\n"
)

    
profile_text = """

IVAN STADNIK

Ridgewood, NJ, USA 

EDUCATION
Georgia Institute of Technology  Jan 2028
Master's, Computer Science

Rutgers, the State University of New Jersey - New Brunswick  May 2025
Bachelor's, Computer Science GPA: 3.3

SKILLS
Languages: Python, Java, SQL
Technologies & Tools: REST APIs, Git, Microservices, Github Actions, Docker, MongoDB, AI tools, Object Oriented Programming
Frameworks: Flask, Express.js, FastAPI
Certifications: Undergraduate Data Science Certificate, AWS Cloud Practitioner, CodePath Intermediate Technical Interview Prep

TECHNICAL PROJECTS
Personify – AI Powered Automated Job Application Tracker 
• Awarded 'Best iCMS Hack' at HackRU Spring 2025 (500+ participants) for developing an AI-powered tool that automated application tracking by extracting company names and job application statuses from emails using Python and OpenAI's GPT-4o mini model

RUCourseFinder – AI-Powered Course & Equivalency Search Tool 
• Engineered a scalable AI-powered search engine using Python, OpenAI embeddings, and vector databases, enabling precise course recommendations for 43,000+ users
• Saved students 10+ minutes per course equivalency search and highlighted more affordable options by automating extraction of 240,000+ location-aware matches across 18 NJ community colleges and 9 Rutgers colleges using Python, Selenium, and pandas

RUPreReq – Interactive Course Prerequisite Visualization 
• Created interactive prerequisite graphs across 165 subjects, helping Rutgers students plan courses more effectively using HTML, CSS, and JavaScript
• Built an ETL pipeline to process complex AND/OR logic for 4,500+ courses, transforming raw data into structured prerequisite combinations using Python and Pandas

Canv.ai – RAG-Powered Educational Chatbot 
• Awarded 'Best Productivity Hack' at HackRU Fall 2024 (400+ participants) for collaborating on a RAG-powered chatbot that outperformed traditional LLMs by leveraging Google's Vertex AI Search and Gemini to accurately answer course-related questions using class materials

Health Journey – Transit Accessibility for Medical Care 
• Awarded "Best Use of NJ Transit Data" at HackRU Fall 2023 (300+ participants) and invited to showcase the project to NJ Transit leadership
• Collaborated with a team to improve transit accessibility for individuals with urgent medical needs by mapping 16,000+ bus stops across 253 routes to nearby medical facilities, using Node.js for efficient data management

PROFESSIONAL EXPERIENCE
Summer Springboard 
Mentor - Duke University / UC San Diego July 2025 - August 2025
• Facilitated college readiness and career exploration workshops for groups of 10–20 high school students, complemented by one-on-one mentorship that strengthened academic goal-setting and personal decision-making skills

Cognizant Remote
Generative AI Extern May 2025 - Jun 2025
• Selected for Cognizant's competitive Generative AI Externship, where I developed AI-driven solutions using Python and large language models (LLMs) to solve business challenges

aiRESULTS Remote
Software Intern Sep 2024 - Oct 2024
• Built a scalable, microservices-based RESTful API for a Customer Loyalty System using Go, Gin, and Docker, optimizing demographic, geographic, and transaction data processing in MongoDB to enable data-driven customer engagement

Silky AI Remote
Software Intern Aug 2024 - Sep 2024
• Led development of a secure and scalable web application that enables users to upload pantry photos and receive personalized meal plans by leveraging Gemini Flash 1.5, the Spoonacular recipe API, Express.js, and MongoDB

Rutgers Blueprint Remote
Back-end Software Engineering Fellow Feb 2024 - Mar 2024
• Selected for competitive fellowship program and gained hands-on experience with Python, HTTP protocols, RESTful APIs, web sockets, and user authentication, while using SQLite for efficient credential storage, fast retrieval, and enhanced security

"""
SYSTEM_PROMPT = (
    "You are Ivan Stadnik's AI career agent. Provide a specific and concise answer based on the user’s question."
    "Use concrete examples and quantified impact from his profile. Connect skills to role needs. "
    "Prefer concise bullets, include metrics, and avoid generic filler.\n\n"
    "You must keep your answer to 250 words or less."
    "Profile: " + profile_text
)

UNRELATED_REPLY = (
    "I'm sorry, I can only answer questions about Ivan Stadnik's profile. "
    "Please ask me about his skills, certifications, projects, or experience."
) 

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

def get_openai_client():

    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client

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
@limiter.limit("4 per day", methods=["POST"])
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
                model="gpt-5-nano",
                messages=messages,
            )
            
            return jsonify({"answer": response.choices[0].message.content})  
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
   


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9000))  
    app.run(debug=True, port=port)
