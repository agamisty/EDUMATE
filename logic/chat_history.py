import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = "data/history.db"


class ChatHistory:
    @staticmethod
    def init_db():
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                pinned INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pinned ON chats(pinned)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON chats(created_at)")
            conn.commit()

    @staticmethod
    def save_chat(chat: Dict):
        if not chat.get("id"):
            chat["id"] = str(uuid.uuid4())
        now = datetime.now().isoformat()
        chat.setdefault("created_at", now)
        chat["updated_at"] = now

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO chats (id, title, question, answer, pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    chat["id"],
                    chat["title"],
                    chat["question"],
                    chat["answer"],
                    int(chat.get("pinned", False)),
                    chat["created_at"],
                    chat["updated_at"],
                ),
            )
            conn.commit()

    @staticmethod
    def load_history(pinned_only: bool = False) -> List[Dict]:
        query = "SELECT * FROM chats ORDER BY created_at DESC"
        if pinned_only:
            query = "SELECT * FROM chats WHERE pinned = 1 ORDER BY created_at DESC"

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            return [ChatHistory.dict_from_row(row) for row in rows]

    @staticmethod
    def get_chat(chat_id: str) -> Optional[Dict]:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
            row = cursor.fetchone()
        return ChatHistory.dict_from_row(row) if row else None

    @staticmethod
    def delete_chat(chat_id: str):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            conn.commit()

    @staticmethod
    def update_title(chat_id: str, new_title: str):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                UPDATE chats SET title = ?, updated_at = ?
                WHERE id = ?
            """,
                (new_title, datetime.now().isoformat(), chat_id),
            )
            conn.commit()

    @staticmethod
    def update_chat(chat_id: str, **updates):  # sourcery skip: merge-list-appends-into-extend, remove-dict-keys
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values())
        values.append(datetime.now().isoformat())
        values.append(chat_id)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                f"UPDATE chats SET {set_clause}, updated_at = ? WHERE id = ?", values
            )
            conn.commit()

    @staticmethod
    def toggle_pin(chat_id: str):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                UPDATE chats SET pinned = NOT pinned, updated_at = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), chat_id),
            )
            conn.commit()

    @staticmethod
    def dict_from_row(row) -> Dict:
        return {
            "id": row[0],
            "title": row[1],
            "question": row[2],
            "answer": row[3],
            "pinned": bool(row[4]),
            "created_at": row[5],
            "updated_at": row[6],
        }


ChatHistory.init_db()
