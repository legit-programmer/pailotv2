from langchain.messages import SystemMessage


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, dict] = {}
        self.base_prompt: SystemMessage = None

    def set_base_prompt(self, base_prompt: SystemMessage):
        self.base_prompt = base_prompt

    def create_session(self, session_id, base_prompt: SystemMessage = None):
        self.sessions[session_id] = {
            "messages": [base_prompt or self.base_prompt],
        }
        

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]