# create_db.py
import sqlite3

DB_PATH = "history.db"


def create_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id TEXT PRIMARY KEY,
            title TEXT,
            question TEXT,
            answer TEXT,
            pinned INTEGER,
            timestamp TEXT
        )
    """
    )
    conn.commit()
    conn.close()
    print("✅ Database 'history.db' created or already exists.")


if __name__ == "__main__":
    create_database()
