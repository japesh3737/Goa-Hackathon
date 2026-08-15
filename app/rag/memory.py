import logging
from typing import List, Dict
from app.config import config

logger = logging.getLogger(__name__)

class ConversationMemory:
    def __init__(self, window_size: int = None):
        self.window_size = window_size or config.MEMORY_WINDOW
        # Stores lists of {"role": "user"|"assistant", "content": "..."}
        self.history: List[Dict[str, str]] = []

    def add_turn(self, user_text: str, assistant_text: str):
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})
        
        # Keep only the last window_size turns (each turn is 2 entries: user + assistant)
        max_entries = self.window_size * 2
        if len(self.history) > max_entries:
            self.history = self.history[-max_entries:]
            
        logger.info(f"Added conversation turn. History size: {len(self.history)} entries.")

    def get_formatted_history(self) -> str:
        if not self.history:
            return ""
            
        formatted = "Recent Conversation History:\n"
        for turn in self.history:
            role = "User" if turn["role"] == "user" else "Agent"
            formatted += f"{role}: {turn['content']}\n"
        formatted += "\n"
        return formatted

    def clear(self):
        self.history = []
        logger.info("Cleared conversation memory.")

# Global Singleton conversation memory
conversation_memory = ConversationMemory()
