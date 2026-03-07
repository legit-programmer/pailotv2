from langchain.messages import SystemMessage
from models.session import Session, CreateSessionRequest


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, Session] = {}
        self.base_prompt: SystemMessage = None

    def set_base_prompt(self, base_prompt: SystemMessage):
        self.base_prompt = base_prompt

    def create_session(self, session: CreateSessionRequest):
        self.sessions[session.session_id] = Session(
            session_id=session.session_id,
            messages=[session.base_prompt or self.base_prompt],
            model=session.model
        )

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def update_session_model(self, session_id: str, new_model: str):
        session = self.get_session(session_id)
        if session:
            session.model = new_model
        else:
            self.create_session(CreateSessionRequest(session_id=session_id, 
            model=new_model))