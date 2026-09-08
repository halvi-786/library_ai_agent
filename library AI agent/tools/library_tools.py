"""
Library AI Agent - watsonx Orchestrate Tools
Four tools exposed to the orchestrate platform:
  1. search_library_books   - full-text search across the catalog
  2. check_book_availability - check copies in stock for a specific title
  3. reserve_library_book    - place a reservation or waitlist entry
  4. get_ai_book_recommendations - call watsonx LLM for personalised suggestions
"""

import json
import requests
from datetime import datetime, timedelta
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

# ── Config ─────────────────────────────────────────────────────────────────────
BACKEND_URL = "http://localhost:5000/api"   # adjust if deployed elsewhere
WATSONX_URL = "https://au-syd.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
WATSONX_API_KEY = "2mmLKomgg--0HR5yh5Y9IWMDf-WqNA_SkZxGYub-cZ5B"
MODEL_ID = "meta-llama/llama-3-3-70b-instruct"
PROJECT_ID = "addfe882-3b61-4b3b-ab5d-d1bf25cbb5dd"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

_token_cache: dict = {"token": None, "expires_at": None}


def _get_iam_token() -> str:
    now = datetime.utcnow()
    if _token_cache["token"] and _token_cache["expires_at"] and _token_cache["expires_at"] > now:
        return _token_cache["token"]
    resp = requests.post(
        IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": WATSONX_API_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + timedelta(seconds=data.get("expires_in", 3600) - 60)
    return _token_cache["token"]


def _call_watsonx(prompt: str) -> str:
    token = _get_iam_token()
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
    resp = requests.post(
        WATSONX_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["results"][0]["generated_text"].strip()


# ── Tool 1: Search Books ───────────────────────────────────────────────────────
@tool(
    name="search_library_books",
    description=(
        "Search the university library catalog for books by keyword, title, author, or subject. "
        "Returns a list of matching books with availability status and copy counts."
    ),
    permission=ToolPermission.READ_ONLY,
)
def search_library_books(query: str, subject: str = "", available_only: bool = False) -> str:
    """
    Search for books in the library.

    Args:
        query: Search keywords (title, author, or topic)
        subject: Optional subject filter (e.g. 'Computer Science', 'Mathematics')
        available_only: If True, return only currently available books

    Returns:
        JSON string listing matching books with availability.
    """
    try:
        params: dict = {}
        if query:
            params["q"] = query
        if subject:
            params["subject"] = subject
        if available_only:
            params["available"] = "true"

        endpoint = f"{BACKEND_URL}/books/search" if query else f"{BACKEND_URL}/books"
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        books = data.get("books", [])

        if not books:
            return json.dumps({"message": f"No books found matching '{query or subject}'.", "books": []})

        summary = [
            {
                "id": b["id"],
                "title": b["title"],
                "author": b["author"],
                "subject": b["subject"],
                "available": b["available"],
                "copies_available": b["copies"],
                "total_copies": b["total_copies"],
                "rating": b["rating"],
                "year": b["year"],
            }
            for b in books[:10]
        ]
        return json.dumps({"count": len(summary), "books": summary})
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})


# ── Tool 2: Check Availability ─────────────────────────────────────────────────
@tool(
    name="check_book_availability",
    description=(
        "Check the real-time availability of a specific book by its ID or by searching its title. "
        "Returns copy count, due dates for checked-out copies, and waitlist length."
    ),
    permission=ToolPermission.READ_ONLY,
)
def check_book_availability(book_id: str = "", title: str = "") -> str:
    """
    Check availability of a specific book.

    Args:
        book_id: The book's ID (e.g. 'B001'). Preferred if known.
        title: Book title to search for if ID is not available.

    Returns:
        JSON string with availability details.
    """
    try:
        if book_id:
            resp = requests.get(f"{BACKEND_URL}/books/{book_id}", timeout=10)
            if resp.status_code == 404:
                return json.dumps({"error": f"Book ID '{book_id}' not found."})
            resp.raise_for_status()
            book = resp.json()
        elif title:
            resp = requests.get(f"{BACKEND_URL}/books/search", params={"q": title}, timeout=10)
            resp.raise_for_status()
            books = resp.json().get("books", [])
            if not books:
                return json.dumps({"error": f"No book found with title containing '{title}'."})
            book = books[0]
        else:
            return json.dumps({"error": "Provide either book_id or title."})

        return json.dumps({
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "available": book["available"],
            "copies_available": book["copies"],
            "total_copies": book["total_copies"],
            "status": "Available" if book["available"] else "All copies checked out — join waitlist",
        })
    except Exception as e:
        return json.dumps({"error": f"Availability check failed: {str(e)}"})


# ── Tool 3: Reserve Book ────────────────────────────────────────────────────────
@tool(
    name="reserve_library_book",
    description=(
        "Reserve a library book for a student. If no copies are available the student is "
        "automatically added to the waitlist. Returns a reservation confirmation ID."
    ),
    permission=ToolPermission.READ_WRITE,
)
def reserve_library_book(book_id: str, student_name: str, student_id: str) -> str:
    """
    Reserve or waitlist a library book.

    Args:
        book_id: The ID of the book to reserve (e.g. 'B001').
        student_name: Full name of the student.
        student_id: University student ID number.

    Returns:
        JSON string with reservation status and ID.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/books/{book_id}/reserve",
            json={"student_name": student_name, "student_id": student_id},
            timeout=10,
        )
        if resp.status_code == 404:
            return json.dumps({"error": f"Book '{book_id}' not found."})
        resp.raise_for_status()
        return json.dumps(resp.json())
    except Exception as e:
        return json.dumps({"error": f"Reservation failed: {str(e)}"})


# ── Tool 4: AI Recommendations ─────────────────────────────────────────────────
@tool(
    name="get_ai_book_recommendations",
    description=(
        "Use IBM watsonx AI (Llama 3.3 70B) to generate personalised book recommendations "
        "for a student based on their query, subject, and academic level. "
        "Returns AI-generated advice plus a list of relevant books from the catalog."
    ),
    permission=ToolPermission.READ_ONLY,
)
def get_ai_book_recommendations(
    query: str,
    subject: str = "",
    level: str = "undergraduate",
) -> str:
    """
    Get AI-powered personalised book recommendations.

    Args:
        query: What the student is studying or looking for (e.g. 'sorting algorithms').
        subject: Optional subject area (e.g. 'Machine Learning').
        level: Academic level — 'undergraduate', 'postgraduate', 'PhD', 'high school'.

    Returns:
        JSON with AI narrative and list of recommended books.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/recommendations",
            json={"query": query, "subject": subject, "level": level},
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        return json.dumps({
            "ai_response": data.get("ai_response", ""),
            "matched_books": data.get("matched_books", []),
        })
    except Exception as e:
        # Fallback: call watsonx directly
        try:
            ai_text = _call_watsonx(
                f"You are a library assistant. Recommend books for a {level} student "
                f"studying '{query or subject}'. Be concise and helpful."
            )
            return json.dumps({"ai_response": ai_text, "matched_books": []})
        except Exception as e2:
            return json.dumps({"error": f"Recommendation failed: {str(e2)}"})
