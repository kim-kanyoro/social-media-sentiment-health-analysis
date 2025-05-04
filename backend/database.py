import sqlite3
import datetime
from hashlib import sha256

# ------------------------
# Database connection setup
# ------------------------

def get_db_connection(db_name="app_database.db"):
    """ Establish and return a database connection. """
    conn = sqlite3.connect(db_name, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # To return rows as dictionaries
    return conn

# ------------------------
# Database Initialization (Create Tables if not exist)
# ------------------------

def create_db():
    """ Create tables if they do not exist. """
    # Users database
    conn_users = get_db_connection("users.db")
    cursor_users = conn_users.cursor()
    cursor_users.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn_users.commit()
    conn_users.close()

    # App database
conn_app = get_db_connection("app_database.db")
cursor_app = conn_app.cursor()

# Create user_posts table
cursor_app.execute('''
    CREATE TABLE IF NOT EXISTS user_posts (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        post_content TEXT,
        sentiment TEXT,
        confidence REAL,
        timestamp TEXT,
        reviewed INTEGER DEFAULT 0
    )
''')

# Create analysis table
cursor_app.execute('''
    CREATE TABLE IF NOT EXISTS analysis (
        id INTEGER PRIMARY KEY,
        data_type TEXT,
        sentiment TEXT,
        confidence REAL,
        timestamp TEXT
    )
''')

# Create alerts table
cursor_app.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        admin_username TEXT,
        comment TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(post_id) REFERENCES user_posts(id) ON DELETE CASCADE
    )
''')

# Commit changes and close connection
conn_app.commit()
conn_app.close()


# ------------------------
# User Management
# ------------------------

def create_user(username, email, password):
    """ Create a new user with hashed password. """
    if user_exists(username) or email_exists(email):
        return False
    hashed_pw = sha256(password.encode()).hexdigest()
    conn = get_db_connection("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        (username, email, hashed_pw)
    )
    conn.commit()
    conn.close()
    return True


def login_user(email, password):
    """ Authenticate user by email and password. """
    hashed_pw = sha256(password.encode()).hexdigest()
    conn = get_db_connection("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, hashed_pw)
    )
    user = cursor.fetchone()
    conn.close()
    return user

# Inside backend/database.py

def update_user(user_id, new_username, new_email):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, "data", "app_database.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET username = ?, email = ? WHERE id = ?
    """, (new_username, new_email, user_id))
    conn.commit()
    conn.close()


def get_flagged_analyses(username):
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "data", "app_database.db")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query to fetch alerts for the logged-in user
    cursor.execute('''
        SELECT a.timestamp, a.sentiment, a.confidence, a.data_type, a.post_content
        FROM alerts a
        INNER JOIN user_posts up ON a.post_id = up.id
        WHERE a.admin_username = ? OR up.username = ?
        ORDER BY a.timestamp DESC
    ''', (username, username))
    
    alerts = cursor.fetchall()
    conn.close()

    # Format the result into a list of dictionaries
    formatted_alerts = [
        {"timestamp": alert[0], "sentiment": alert[1], "confidence": alert[2], "data_type": alert[3], "post_content": alert[4]}
        for alert in alerts
    ]
    
    return formatted_alerts


def user_exists(username):
    """ Check if a username exists in the database. """
    conn = get_db_connection("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE username=?",
        (username,)
    )
    exists = cursor.fetchone()
    conn.close()
    return exists is not None


def email_exists(email):
    """ Check if an email already exists in the database. """
    conn = get_db_connection("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE email=?",
        (email,)
    )
    exists = cursor.fetchone()
    conn.close()
    return exists is not None


def get_all_users():
    """ Get all users in the database. """
    conn = get_db_connection("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email FROM users"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

# ------------------------
# User-specific Analysis
# ------------------------

def get_user_analysis(user_email):
    """Return sentiment counts for the given user email."""
    # 1) Find username by email
    conn_u = get_db_connection("users.db")
    cur_u = conn_u.cursor()
    cur_u.execute(
        "SELECT username FROM users WHERE email = ?",
        (user_email,)
    )
    row = cur_u.fetchone()
    conn_u.close()
    if not row:
        return None
    username = row["username"]

    

    # 2) Count posts by sentiment
    conn = get_db_connection("app_database.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM user_posts WHERE username = ?",
        (username,)
    )
    total = cur.fetchone()[0]
    stats = {"total": total}

    for sentiment in ("positive", "negative", "neutral"):
        cur.execute(
            "SELECT COUNT(*) FROM user_posts WHERE username = ? AND sentiment = ?",
            (username, sentiment)
        )
        stats[sentiment] = cur.fetchone()[0]
    conn.close()
    return stats

def delete_user(user_id):
    """ Delete a user by their ID. """
    conn = get_db_connection("users.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_user(user_id, username=None, email=None, password=None):
    """ Update user details (username, email, or password). """
    conn = get_db_connection("users.db")
    cursor = conn.cursor()

    # Prepare the update query
    update_fields = []
    params = []

    if username:
        update_fields.append("username = ?")
        params.append(username)
    
    if email:
        update_fields.append("email = ?")
        params.append(email)
    
    if password:
        hashed_pw = sha256(password.encode()).hexdigest()
        update_fields.append("password = ?")
        params.append(hashed_pw)
    
    # Update only if there are fields to update
    if update_fields:
        set_clause = ", ".join(update_fields)
        query = f"UPDATE users SET {set_clause} WHERE id = ?"
        params.append(user_id)
        cursor.execute(query, tuple(params))
        conn.commit()
    
    conn.close()


# ------------------------
# Post and Analysis
# ------------------------

def save_user_post(username, post_content, sentiment, confidence):
    """ Save user posts with sentiment analysis. """
    timestamp = datetime.datetime.now().isoformat()
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO user_posts (username, post_content, sentiment, confidence, timestamp)
           VALUES (?, ?, ?, ?, ?)''',
        (username, post_content, sentiment, confidence, timestamp)
    )
    conn.commit()

    cursor.execute(
        '''INSERT INTO analysis (data_type, sentiment, confidence, timestamp)
           VALUES (?, ?, ?, ?)''',
        ("post", sentiment, confidence, timestamp)
    )
    conn.commit()
    conn.close()


def save_analysis_result(data_type, sentiment, confidence):
    """ Save generic sentiment analysis results. """
    timestamp = datetime.datetime.now().isoformat()
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO analysis (data_type, sentiment, confidence, timestamp)
           VALUES (?, ?, ?, ?)''',
        (data_type, sentiment, confidence, timestamp)
    )
    conn.commit()
    conn.close()

def get_user_analysis(user_email):
    """Return sentiment counts for the given user email."""
    try:
        # 1) Find username by email
        conn_u = get_db_connection("users.db")
        cur_u = conn_u.cursor()
        cur_u.execute(
            "SELECT username FROM users WHERE email = ?",
            (user_email,)
        )
        row = cur_u.fetchone()
        conn_u.close()
        
        if not row:
            print(f"User with email {user_email} not found.")
            return None
        username = row["username"]

        # 2) Count posts by sentiment
        conn = get_db_connection("app_database.db")
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM user_posts WHERE username = ?",
            (username,)
        )
        total = cur.fetchone()[0]
        stats = {"total": total}

        for sentiment in ("positive", "negative", "neutral"):
            cur.execute(
                "SELECT COUNT(*) FROM user_posts WHERE username = ? AND sentiment = ?",
                (username, sentiment)
            )
            stats[sentiment] = cur.fetchone()[0]
        conn.close()

        print(f"Sentiment Data for {user_email} ({username}): {stats}")
        return stats

    except Exception as e:
        print(f"Error getting user analysis for {user_email}: {e}")
        return None

def get_user_analysis(user_email):
    """Return sentiment counts and average confidence for the given user email."""
    try:
        # 1) Find username by email
        conn_u = get_db_connection("users.db")
        cur_u = conn_u.cursor()
        cur_u.execute(
            "SELECT username FROM users WHERE email = ?",
            (user_email,)
        )
        row = cur_u.fetchone()
        conn_u.close()

        if not row:
            print(f"User with email {user_email} not found.")
            return None
        username = row["username"]

        # 2) Count posts by sentiment and average confidence
        conn = get_db_connection("app_database.db")
        cur = conn.cursor()

        # Get total posts for the user
        cur.execute(
            "SELECT COUNT(*) FROM user_posts WHERE username = ?",
            (username,)
        )
        total = cur.fetchone()[0]

        # Initialize the confidence values
        positive_confidence = 0.0
        negative_confidence = 0.0
        neutral_confidence = 0.0

        # Initialize the sentiment count
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

        for sentiment in ("positive", "negative", "neutral"):
            # Count the posts for each sentiment
            cur.execute(
                "SELECT COUNT(*), AVG(confidence) FROM user_posts WHERE username = ? AND sentiment = ?",
                (username, sentiment)
            )
            count, avg_confidence = cur.fetchone()
            sentiment_counts[sentiment] = count

            # Add the confidence to the respective variable
            if sentiment == "positive":
                positive_confidence = avg_confidence or 0
            elif sentiment == "negative":
                negative_confidence = avg_confidence or 0
            elif sentiment == "neutral":
                neutral_confidence = avg_confidence or 0

        conn.close()

        stats = {
            "total": total,
            "positive": sentiment_counts["positive"],
            "negative": sentiment_counts["negative"],
            "neutral": sentiment_counts["neutral"],
            "positive_confidence": positive_confidence,
            "negative_confidence": negative_confidence,
            "neutral_confidence": neutral_confidence
        }

        return stats

    except Exception as e:
        print(f"Error getting user analysis for {user_email}: {e}")
        return None


def get_analysis_stats():
    """ Get overall sentiment analysis stats. """
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM analysis")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM analysis WHERE sentiment='positive'")
    positive = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM analysis WHERE sentiment='negative'")
    negative = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM analysis WHERE sentiment='neutral'")
    neutral = cursor.fetchone()[0]
    conn.close()
    return {
        "total_analyzed": total,
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral
    }


def get_flagged_analyses():
    """ Retrieve negative posts flagged for review. """
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, post_content, sentiment, confidence, timestamp
        FROM user_posts
        WHERE sentiment = 'negative'
        ORDER BY timestamp DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r["id"], "username": r["username"], "post_content": r["post_content"],
         "sentiment": r["sentiment"], "confidence": r["confidence"], "timestamp": r["timestamp"]}
        for r in rows
    ]


def get_all_analyses():
    """ Retrieve all posts with their sentiments. """
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, post_content, sentiment, confidence, timestamp
        FROM user_posts
        ORDER BY timestamp DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r["id"], "username": r["username"], "post_content": r["post_content"],
         "sentiment": r["sentiment"], "confidence": r["confidence"], "timestamp": r["timestamp"]}
        for r in rows
    ]


def mark_as_reviewed(flag_id):
    """ Mark a flagged post as reviewed. """
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_posts SET reviewed = 1 WHERE id = ?",
        (flag_id,)
    )
    conn.commit()
    conn.close()


def get_all_posts():
    """ Get all user posts. """
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_posts ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ------------------------
# System Statistics
# ------------------------

def get_system_stats():
    """ Retrieve overall system stats. """
    conn = get_db_connection("app_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_posts")
    total_posts = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM user_posts WHERE sentiment = 'negative'")
    negative_posts = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT username) FROM user_posts")
    total_users = cursor.fetchone()[0]
    conn.close()
    return {
        "total_posts": total_posts,
        "negative_posts": negative_posts,
        "total_users": total_users
    }

# ------------------------
# Initialize database on import
# ------------------------
create_db()
