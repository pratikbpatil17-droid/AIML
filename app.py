from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
import json
from datetime import datetime

app = Flask(__name__)

DB_NAME = "store.db"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:latest"


# --------------------------
# DATABASE
# --------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_message TEXT,
        bot_response TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# --------------------------
# LOAD JSON KNOWLEDGE
# --------------------------
def load_knowledge():
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


knowledge = load_knowledge()


# --------------------------
# SEARCH JSON KNOWLEDGE
# --------------------------
def get_context(user_message):
    msg = user_message.lower()

    for key, value in knowledge.items():
        if key.lower() in msg:
            return value

    return ""


# --------------------------
# SAVE CHAT
# --------------------------
def save_chat(user_msg, bot_msg):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO chats
        (user_message, bot_response, created_at)
        VALUES (?, ?, ?)
    """, (
        user_msg,
        bot_msg,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# --------------------------
# OLLAMA REQUEST
# --------------------------
def ask_ollama(message):

    context = get_context(message)

    prompt = f"""
    You are a helpful AI assistant.

    Context:
    {context}

    User:
    {message}
    """

    payload = {
        "model": "llama3.2:latest",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=120
    )

    result = response.json()

    return result.get("response", "No response generated.")


# --------------------------
# ROUTES
# --------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():

    user_message = request.json.get("message")

    if not user_message:
        return jsonify({
            "response": "Please enter a message."
        })

    bot_response = ask_ollama(user_message)

    save_chat(user_message, bot_response)

    return jsonify({
        "response": bot_response
    })


@app.route("/history")
def history():

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT user_message,
           bot_response,
           created_at
    FROM chats
    ORDER BY id DESC
    LIMIT 50
    """)

    rows = cur.fetchall()
    conn.close()

    data = []

    for row in rows:
        data.append({
            "user": row[0],
            "bot": row[1],
            "time": row[2]
        })

    return jsonify(data)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)