import os
import requests
import math
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------
# LIFESPAN (Replaces @app.on_event)
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto open browser on startup
    webbrowser.open("http://localhost:8000")
    yield
    # Any teardown/cleanup code would go here

app = FastAPI(lifespan=lifespan)

# -----------------------------
# CORS
# -----------------------------
# Allow all origins so the frontend (served from any host/port) can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# API KEY
# -----------------------------
API_KEY = "api_key_here"  # Make sure to secure this in production (e.g., using .env)

# -----------------------------
# DATA MODELS
# -----------------------------
class UserProfile(BaseModel):
    """Pydantic model representing a user's financial profile.

    Attributes:
        age:         Current age of the user (years).
        income:      Monthly gross income (₹).
        expenses:    Monthly living expenses (₹).
        savings:     Total liquid savings / emergency fund (₹).
        investments: Monthly SIP / investment amount (₹).
        debt:        Total outstanding debt principal (₹).
        emi:         Monthly EMI obligation (₹).
        insurance:   Insurance coverage type: "none" | "health" | "term" | "both".
        risk:        Risk appetite: "conservative" | "moderate" | "aggressive".
        retireAge:   Target retirement age (years).
    """

    age: int
    income: float
    expenses: float
    savings: float
    investments: float
    debt: float
    emi: float
    insurance: str
    risk: str
    retireAge: int

class ChatRequest(BaseModel):
    message: str
    profile: dict

# -----------------------------
# LOGIC
# -----------------------------
def calculate_score(p: UserProfile):
    scores = {}

    months = p.savings / max(p.expenses, 1)
    scores["emergency"] = 100 if months >= 6 else 70 if months >= 3 else 40

    ratio = p.emi / max(p.income, 1)
    scores["debt"] = 100 if ratio < 0.3 else 60 if ratio < 0.5 else 30

    rate = p.investments / max(p.income, 1)
    scores["savings"] = 100 if rate >= 0.2 else 60 if rate >= 0.1 else 30

    scores["insurance"] = 100 if p.insurance == "both" else 50
    scores["investment"] = 80 if rate >= 0.15 else 50
    scores["retirement"] = 70 if p.savings > 200000 else 40

    total = sum(scores.values()) // len(scores)

    return {"total": total, "breakdown": scores}

def calculate_fire(p: UserProfile):
    years = p.retireAge - p.age
    r = 0.12 / 12
    n = years * 12

    sip = p.investments

    fv = sip * ((1 + r)**n - 1) / r
    lump = p.savings * (1.12 ** years)

    total = fv + lump

    return {"years": years, "corpus": round(total, 2)}

# -----------------------------
# AI CHAT
# -----------------------------
def financial_agent(query: str, profile: dict, mode: str = "chat"):
    if not profile:
        profile = {}
        
    try:
        prompt = f"""
You are a financial advisor.

User:
Income: ₹{profile.get('income', 0)}
Expenses: ₹{profile.get('expenses', 0)}
Savings: ₹{profile.get('savings', 0)}

{ "Give 4 short suggestions." if mode == "suggestions" else f"Answer: {query}" }
"""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        # Trigger the except block if the HTTP request failed (e.g., bad API key)
        response.raise_for_status()

        data = response.json()
        print("FULL API RESPONSE:", data)

        if "choices" not in data or not data["choices"]:
            return f"API Error: Unexpected payload format. {data}"

        return data["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        print("NETWORK/API ERROR:", e)
        return "AI connection failed. Check your API key and network."
    except Exception as e:
        print("AI ERROR:", e)
        return "AI failed. Check backend logs."

# -----------------------------
# ROUTES
# -----------------------------
@app.post("/analyze")
def analyze(profile: UserProfile):
    score_data = calculate_score(profile)
    fire_data = calculate_fire(profile)

    suggestions_text = financial_agent(
        query="",
        profile=profile.model_dump(),  # ✅ Updated from .dict() for Pydantic v2
        mode="suggestions"
    )

    suggestions = [
        s.strip("-• ")
        for s in suggestions_text.split("\n")
        if s.strip()
    ]

    return {
        "score": score_data,
        "fire": fire_data,
        "suggestions": suggestions
    }

@app.post("/chat")
def chat(data: ChatRequest):  # ✅ Uses proper Pydantic validation now
    reply = financial_agent(
        query=data.message,
        profile=data.profile,
        mode="chat"
    )

    return {"reply": reply}

# -----------------------------
# SERVE FRONTEND
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    file_path = "fire_advisor_updated.html"
    
    # ✅ Prevent server crash if HTML file is missing
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Frontend file '{file_path}' not found.")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
        debt: float
    emi: float
    insurance: str
    risk: str
    retireAge: int

# -----------------------------
# LOGIC (from logic.py)
# -----------------------------
def calculate_score(p: UserProfile) -> dict:
    """Calculate a holistic financial health score for the user.

    Evaluates six pillars — emergency fund, debt, savings rate, insurance,
    investment habit, and retirement readiness — and returns an overall score
    (0-100) plus a per-pillar breakdown.

    Args:
        p: A :class:`UserProfile` instance with the user's financial data.

    Returns:
        A dict with keys:
          - ``"total"`` (int): Average score across all pillars (0-100).
          - ``"breakdown"`` (dict): Individual scores for each pillar.
    """
    scores = {}

    # Emergency fund: measure months of expenses covered by savings
    months = p.savings / max(p.expenses, 1)
    scores["emergency"] = 100 if months >= 6 else 70 if months >= 3 else 40

    # Debt health: EMI-to-income ratio (lower is better)
    ratio = p.emi / max(p.income, 1)
    scores["debt"] = 100 if ratio < 0.3 else 60 if ratio < 0.5 else 30

    # Savings rate: monthly investments as a fraction of income
    rate = p.investments / max(p.income, 1)
    scores["savings"] = 100 if rate >= 0.2 else 60 if rate >= 0.1 else 30

    # Insurance: full marks only when both term and health cover are held
    scores["insurance"] = 100 if p.insurance == "both" else 50

    # Investment habit: rewards users who invest ≥15% of income monthly
    scores["investment"] = 80 if rate >= 0.15 else 50

    # Retirement readiness: simple savings threshold check
    scores["retirement"] = 70 if p.savings > 200000 else 40

    # Overall score is the integer average of all pillar scores
    total = sum(scores.values()) // len(scores)

    return {"total": total, "breakdown": scores}


def calculate_fire(p: UserProfile) -> dict:
    """Project the user's FIRE corpus using SIP future-value math.

    Assumes a 12 % annual return (compounded monthly) for both the SIP stream
    and the existing lump-sum savings.

    Args:
        p: A :class:`UserProfile` instance with the user's financial data.

    Returns:
        A dict with keys:
          - ``"years"`` (int): Years remaining until target retirement age.
          - ``"corpus"`` (float): Projected corpus at retirement (₹), rounded
            to 2 decimal places.
    """
    years = p.retireAge - p.age  # Investment horizon in years
    r = 0.12 / 12                # Monthly interest rate (12% p.a.)
    n = years * 12               # Total number of monthly investments

    sip = p.investments  # Monthly SIP amount (₹)

    # Future value of the SIP stream: FV = SIP × [(1+r)^n − 1] / r
    fv = sip * ((1 + r)**n - 1) / r

    # Future value of existing lump-sum savings compounded annually
    lump = p.savings * (1.12 ** years)

    total = fv + lump

    return {"years": years, "corpus": round(total, 2)}

# -----------------------------
# AI CHAT (from ai.py)
# -----------------------------
def financial_agent(query: str, profile: dict, mode: str = "chat") -> str:
    """Send a prompt to the Groq LLM and return the AI's response.

    Constructs a context-aware prompt using the user's financial profile and
    either asks the model for personalised suggestions or answers a specific
    query, depending on ``mode``.

    Args:
        query:   The user's free-text question (ignored when mode="suggestions").
        profile: A plain dict containing the user's financial profile keys
                 (income, expenses, savings, …).
        mode:    ``"suggestions"`` to request 4 short proactive tips, or
                 ``"chat"`` to answer the user's specific ``query``.

    Returns:
        The model's reply as a string, or an error message if the call fails.
    """
    try:
        # Build a short financial-context block so the LLM is grounded in the
        # user's actual numbers rather than giving generic advice.
        prompt = f"""
You are a financial advisor.

User:
Income: ₹{profile.get('income')}
Expenses: ₹{profile.get('expenses')}
Savings: ₹{profile.get('savings')}

{ "Give 4 short suggestions." if mode=="suggestions" else f"Answer: {query}" }
"""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        data = response.json()

        # Log the full API response to aid debugging during development
        print("FULL API RESPONSE:", data)

        # Guard against unexpected API error shapes that lack "choices"
        if "choices" not in data:
            return f"API Error: {data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI ERROR:", e)
        return "AI failed. Check backend."

# -----------------------------
# ROUTES
# -----------------------------
@app.post("/analyze")
def analyze(profile: UserProfile):
    """Analyse a user's financial profile and return score, FIRE projection, and AI suggestions.

    POST body: JSON matching :class:`UserProfile`.

    Returns:
        JSON with three keys:
          - ``score``: financial health score and per-pillar breakdown.
          - ``fire``: projected FIRE corpus and time horizon.
          - ``suggestions``: list of AI-generated personalised tips.
    """
    # Compute the rule-based financial health score
    score_data = calculate_score(profile)

    # Project the retirement corpus using SIP future-value formula
    fire_data = calculate_fire(profile)

    # Ask the AI for 4 short suggestions tailored to this profile
    suggestions_text = financial_agent(
        query="",
        profile=profile.dict(),
        mode="suggestions"
    )

    # Split the AI response into a clean list, stripping bullet/dash markers
    suggestions = [
        s.strip("-• ")
        for s in suggestions_text.split("\n")
        if s.strip()
    ]

    return {
        "score": score_data,
        "fire": fire_data,
        "suggestions": suggestions
    }

@app.post("/chat")
def chat(data: dict):
    """Handle a free-text chat message from the user.

    POST body:
        ``message`` (str): The user's question.
        ``profile``  (dict): Current financial profile for AI context (optional).

    Returns:
        JSON with key ``reply`` containing the AI's answer.
    """
    message = data.get("message")
    profile = data.get("profile")

    reply = financial_agent(
        query=message,
        profile=profile,
        mode="chat"
    )

    return {"reply": reply}

# -----------------------------
# SERVE FRONTEND
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the WealthSutra single-page frontend.

    Reads ``fire_advisor_updated.html`` from the working directory and returns
    it as an HTML response so users can access the app at http://localhost:8000/.
    """
    with open("fire_advisor_updated.html", "r", encoding="utf-8") as f:
        return f.read()

@app.on_event("startup")
def open_browser():
    webbrowser.open("http://localhost:8000")
