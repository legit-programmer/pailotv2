import sqlite3
import json
from langchain_core.messages import SystemMessage, messages_to_dict, messages_from_dict
from models.session import Session, CreateSessionRequest



class SessionManager:
    def __init__(self, db_path="sessions.db"):
        self.db_path = db_path
        self.sessions: dict[str, Session] = {}
        self.base_prompt: SystemMessage = None
        self._init_db()
        self.active_loops = set()
        self.message_queues = {}

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    model TEXT,
                    messages TEXT
                )
            ''')
            conn.commit()

    def set_base_prompt(self, base_prompt: SystemMessage):
        self.base_prompt = base_prompt

    def create_session(self, session: CreateSessionRequest):
        new_session = Session(
            session_id=session.session_id,
            messages=[],
            model=session.model
        )
        self.save_session(new_session)

    def get_session(self, session_id: str):
        if session_id in self.sessions:
            return self.sessions[session_id]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT model, messages FROM sessions WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                model, messages_json = row
                messages_dict = json.loads(messages_json)
                messages = messages_from_dict(messages_dict)
                # Filter out any old SystemMessages that might have been saved in previous versions
                messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
                session = Session(session_id=session_id, model=model, messages=messages)
                self.sessions[session_id] = session
                return session
        return None

    def save_session(self, session: Session):
        self.sessions[session.session_id] = session
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Do not save SystemMessages to the database, only user/assistant history.
            history = [msg for msg in session.messages if not isinstance(msg, SystemMessage)]
            messages_json = json.dumps(messages_to_dict(history))
            cursor.execute('''
                INSERT INTO sessions (session_id, model, messages)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    model=excluded.model,
                    messages=excluded.messages
            ''', (session.session_id, session.model, messages_json))
            conn.commit()

    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            conn.commit()

    def update_session_model(self, session_id: str, new_model: str):
        session = self.get_session(session_id)
        if session:
            session.model = new_model
            self.save_session(session)
        else:
            self.create_session(CreateSessionRequest(session_id=session_id, model=new_model))

    def is_loop_active(self, session_id: str) -> bool:
        return session_id in self.active_loops
    
    def get_steering_messages(self, session_id: str) -> list[str]:
        messages = self.message_queues.get(session_id, [])
        self.clear_steering_messages(session_id)
        return messages
    
    def add_steering_message(self, session_id: str, message: str):
        if session_id not in self.message_queues:
            self.message_queues[session_id] = []
        self.message_queues[session_id].append(message)

    def clear_steering_messages(self, session_id: str):
        self.message_queues[session_id] = []