"""
Library AI Agent - Backend Server
Provides REST API endpoints for book search, availability, reservations,
and AI-powered recommendations via IBM watsonx.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ─── watsonx Config ────────────────────────────────────────────────────────────
WATSONX_URL = "https://au-syd.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
WATSONX_API_KEY = "2mmLKomgg--0HR5yh5Y9IWMDf-WqNA_SkZxGYub-cZ5B"
MODEL_ID = "meta-llama/llama-3-3-70b-instruct"
PROJECT_ID = "addfe882-3b61-4b3b-ab5d-d1bf25cbb5dd"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# ─── Mock Library Database ─────────────────────────────────────────────────────
LIBRARY_DB = [
    {"id": "B001", "title": "Introduction to Algorithms", "author": "Cormen et al.", "subject": "Computer Science", "available": True, "copies": 3, "total_copies": 5, "isbn": "9780262033848", "year": 2022, "rating": 4.8},
    {"id": "B002", "title": "Clean Code", "author": "Robert C. Martin", "subject": "Software Engineering", "available": True, "copies": 2, "total_copies": 3, "isbn": "9780132350884", "year": 2008, "rating": 4.7},
    {"id": "B003", "title": "The Pragmatic Programmer", "author": "Hunt & Thomas", "subject": "Software Engineering", "available": False, "copies": 0, "total_copies": 2, "isbn": "9780135957059", "year": 2019, "rating": 4.9},
    {"id": "B004", "title": "Artificial Intelligence: A Modern Approach", "author": "Russell & Norvig", "subject": "Artificial Intelligence", "available": True, "copies": 1, "total_copies": 4, "isbn": "9780134610993", "year": 2020, "rating": 4.6},
    {"id": "B005", "title": "Deep Learning", "author": "Goodfellow et al.", "subject": "Machine Learning", "available": True, "copies": 2, "total_copies": 3, "isbn": "9780262035613", "year": 2016, "rating": 4.7},
    {"id": "B006", "title": "Design Patterns", "author": "Gang of Four", "subject": "Software Engineering", "available": True, "copies": 4, "total_copies": 4, "isbn": "9780201633610", "year": 1994, "rating": 4.5},
    {"id": "B007", "title": "Computer Networks", "author": "Tanenbaum & Wetherall", "subject": "Networking", "available": False, "copies": 0, "total_copies": 3, "isbn": "9780132126953", "year": 2010, "rating": 4.4},
    {"id": "B008", "title": "Operating System Concepts", "author": "Silberschatz et al.", "subject": "Operating Systems", "available": True, "copies": 2, "total_copies": 4, "isbn": "9781119800361", "year": 2018, "rating": 4.3},
    {"id": "B009", "title": "Database System Concepts", "author": "Silberschatz et al.", "subject": "Databases", "available": True, "copies": 3, "total_copies": 5, "isbn": "9780078022159", "year": 2019, "rating": 4.5},
    {"id": "B010", "title": "Python Crash Course", "author": "Eric Matthes", "subject": "Programming", "available": True, "copies": 5, "total_copies": 6, "isbn": "9781593279288", "year": 2019, "rating": 4.8},
    {"id": "B011", "title": "Machine Learning with Python", "author": "Andreas Müller", "subject": "Machine Learning", "available": True, "copies": 2, "total_copies": 3, "isbn": "9781449369415", "year": 2016, "rating": 4.6},
    {"id": "B012", "title": "Structure and Interpretation of Computer Programs", "author": "Abelson & Sussman", "subject": "Computer Science", "available": True, "copies": 1, "total_copies": 2, "isbn": "9780262510875", "year": 1996, "rating": 4.7},
    {"id": "B013", "title": "Data Structures and Algorithm Analysis", "author": "Mark Allen Weiss", "subject": "Computer Science", "available": False, "copies": 0, "total_copies": 3, "isbn": "9780132576277", "year": 2011, "rating": 4.3},
    {"id": "B014", "title": "Calculus: Early Transcendentals", "author": "James Stewart", "subject": "Mathematics", "available": True, "copies": 6, "total_copies": 8, "isbn": "9781285741550", "year": 2015, "rating": 4.4},
    {"id": "B015", "title": "Linear Algebra and Its Applications", "author": "Gilbert Strang", "subject": "Mathematics", "available": True, "copies": 3, "total_copies": 4, "isbn": "9780030105678", "year": 2016, "rating": 4.6},
]

RESERVATIONS = {}
_iam_token_cache = {"token": None, "expires_at": None}


# ─── IAM Token Helper ──────────────────────────────────────────────────────────
def get_iam_token():
    now = datetime.utcnow()
    if _iam_token_cache["token"] and _iam_token_cache["expires_at"] > now:
        return _iam_token_cache["token"]

    resp = requests.post(
        IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": WATSONX_API_KEY,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _iam_token_cache["token"] = data["access_token"]
    _iam_token_cache["expires_at"] = now + timedelta(seconds=data.get("expires_in", 3600) - 60)
    return _iam_token_cache["token"]


# ─── watsonx AI Helper ─────────────────────────────────────────────────────────
def call_watsonx(prompt: str) -> str:
    token = get_iam_token()
    payload = {
        "model_id": MODEL_ID,
        "project_id": PROJECT_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 600,
            "temperature": 0.7,
            "stop_sequences": ["Human:", "User:"],
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = requests.post(WATSONX_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    result = resp.json()
    return result["results"][0]["generated_text"].strip()


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Library AI Agent Backend", "timestamp": datetime.utcnow().isoformat()})


@app.route("/api/books", methods=["GET"])
def list_books():
    """Return all books, optionally filtered by subject or availability."""
    subject = request.args.get("subject", "").lower()
    available_only = request.args.get("available", "false").lower() == "true"
    books = LIBRARY_DB
    if subject:
        books = [b for b in books if subject in b["subject"].lower()]
    if available_only:
        books = [b for b in books if b["available"]]
    return jsonify({"books": books, "count": len(books)})


@app.route("/api/books/search", methods=["GET"])
def search_books():
    """Search books by query string across title, author, and subject."""
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify({"books": [], "count": 0})
    results = [
        b for b in LIBRARY_DB
        if query in b["title"].lower()
        or query in b["author"].lower()
        or query in b["subject"].lower()
    ]
    return jsonify({"books": results, "count": len(results)})


@app.route("/api/books/<book_id>", methods=["GET"])
def get_book(book_id):
    """Get a single book by ID."""
    book = next((b for b in LIBRARY_DB if b["id"] == book_id), None)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book)


@app.route("/api/books/<book_id>/reserve", methods=["POST"])
def reserve_book(book_id):
    """Reserve or join waitlist for a book."""
    data = request.get_json() or {}
    student_name = data.get("student_name", "Anonymous")
    student_id = data.get("student_id", "S000")

    book = next((b for b in LIBRARY_DB if b["id"] == book_id), None)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    reservation_id = f"RES-{book_id}-{student_id}-{int(datetime.utcnow().timestamp())}"
    due_date = (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d")

    if book["available"] and book["copies"] > 0:
        book["copies"] -= 1
        if book["copies"] == 0:
            book["available"] = False
        RESERVATIONS[reservation_id] = {
            "id": reservation_id,
            "book_id": book_id,
            "book_title": book["title"],
            "student_name": student_name,
            "student_id": student_id,
            "status": "confirmed",
            "due_date": due_date,
            "created_at": datetime.utcnow().isoformat(),
        }
        return jsonify({
            "success": True,
            "reservation_id": reservation_id,
            "status": "confirmed",
            "due_date": due_date,
            "message": f"Reservation confirmed! Please collect '{book['title']}' by {due_date}.",
        })
    else:
        RESERVATIONS[reservation_id] = {
            "id": reservation_id,
            "book_id": book_id,
            "book_title": book["title"],
            "student_name": student_name,
            "student_id": student_id,
            "status": "waitlisted",
            "created_at": datetime.utcnow().isoformat(),
        }
        return jsonify({
            "success": True,
            "reservation_id": reservation_id,
            "status": "waitlisted",
            "message": f"Added to waitlist for '{book['title']}'. We'll notify you when available.",
        })


@app.route("/api/recommendations", methods=["POST"])
def get_recommendations():
    """AI-powered book recommendations based on student profile and query."""
    data = request.get_json() or {}
    query = data.get("query", "")
    subject = data.get("subject", "")
    level = data.get("level", "undergraduate")

    # Build context from library
    available_titles = [
        f"- {b['title']} by {b['author']} ({b['subject']}) - {'Available' if b['available'] else 'Not available'}"
        for b in LIBRARY_DB
    ]
    book_list = "\n".join(available_titles)

    prompt = f"""You are a knowledgeable library assistant AI. A {level} student needs help finding the right books.

Student query: "{query}"
Subject area of interest: "{subject or 'General'}"

Available books in the library:
{book_list}

Based on the student's query and the available books, provide:
1. Top 3-5 specific book recommendations from the list above with clear reasons
2. Why each book is suitable for this student
3. A suggested reading order if applicable
4. Any additional study tips

Be concise, helpful, and focus on books that are available. Format your response clearly."""

    try:
        ai_response = call_watsonx(prompt)
    except Exception as e:
        ai_response = f"I recommend searching our catalog for books on '{query or subject}'. Our top-rated books in this area include titles by leading authors. Please use the search feature to find available copies."

    # Also return matching books from the DB
    search_term = (query + " " + subject).lower()
    matched_books = [
        b for b in LIBRARY_DB
        if any(word in b["title"].lower() or word in b["subject"].lower()
               for word in search_term.split() if len(word) > 2)
    ][:5]

    return jsonify({
        "ai_response": ai_response,
        "matched_books": matched_books,
        "query": query,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """General AI chat for library assistance."""
    data = request.get_json() or {}
    message = data.get("message", "")
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Message required"}), 400

    # Build conversation context
    conversation = ""
    for turn in history[-6:]:  # last 6 turns for context
        conversation += f"Student: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}\n"

    subjects = list({b["subject"] for b in LIBRARY_DB})
    available_count = sum(1 for b in LIBRARY_DB if b["available"])

    prompt = f"""You are a helpful Library AI Assistant at a university library. You help students find books, check availability, make reservations, and get study recommendations.

Library facts:
- Total books: {len(LIBRARY_DB)}
- Currently available: {available_count}
- Subjects covered: {', '.join(subjects)}

{f'Previous conversation:{chr(10)}{conversation}' if conversation else ''}
Student: {message}
Assistant:"""

    try:
        response = call_watsonx(prompt)
    except Exception as e:
        response = "I'm here to help you find books and learning resources! You can ask me to search for books, check availability, or get personalized recommendations based on your course."

    return jsonify({"response": response, "timestamp": datetime.utcnow().isoformat()})


@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    """Return all unique subjects in the library."""
    subjects = sorted(list({b["subject"] for b in LIBRARY_DB}))
    return jsonify({"subjects": subjects})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Return library statistics."""
    total = len(LIBRARY_DB)
    available = sum(1 for b in LIBRARY_DB if b["available"])
    subjects = len({b["subject"] for b in LIBRARY_DB})
    total_copies = sum(b["total_copies"] for b in LIBRARY_DB)
    return jsonify({
        "total_titles": total,
        "available_titles": available,
        "unavailable_titles": total - available,
        "total_subjects": subjects,
        "total_copies": total_copies,
        "total_reservations": len(RESERVATIONS),
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
