"""
Conversation Manager - Persist and load conversation history
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class ConversationManager:
    """Manage persistent conversation storage"""
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize conversation manager
        
        Args:
            storage_dir: Directory to store conversation files
        """
        if storage_dir is None:
            from src.config import config
            storage_dir = config.CONVERSATION_DIR
        
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_conversation_ids: Dict[str, str] = {}
    
    def _sanitize_session_token(self, session_token: str) -> str:
        if not session_token:
            return "anonymous"
        safe_token = ''.join(ch for ch in session_token if ch.isalnum() or ch in '-_')
        return safe_token or "anonymous"
    
    def _get_session_dir(self, session_token: str) -> Path:
        token = self._sanitize_session_token(session_token)
        path = self.storage_dir / token
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def _get_conversation_file(self, conversation_id: str, session_token: str) -> Path:
        return self._get_session_dir(session_token) / f"{conversation_id}.json"
    
    def _get_active_conversation_id(self, session_token: str) -> Optional[str]:
        token = self._sanitize_session_token(session_token)
        return self.current_conversation_ids.get(token)
    
    def _set_active_conversation_id(self, conversation_id: Optional[str], session_token: str):
        token = self._sanitize_session_token(session_token)
        if conversation_id is None:
            self.current_conversation_ids.pop(token, None)
        else:
            self.current_conversation_ids[token] = conversation_id
    
    def create_conversation(self, title: str = None, session_token: str = None) -> str:
        """
        Create a new conversation for a specific session
        
        Args:
            title: Optional title for the conversation
            session_token: Session token for user isolation
        
        Returns:
            Conversation ID (timestamp-based)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        conversation_id = f"conv_{timestamp}"
        
        if title is None:
            title = f"Conversation - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        metadata = {
            "id": conversation_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        
        file_path = self._get_conversation_file(conversation_id, session_token)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
        except IOError as e:
            print(f"Error writing conversation file: {e}")
            return conversation_id
        
        self._set_active_conversation_id(conversation_id, session_token)
        print(f"Created conversation: {conversation_id} for session {self._sanitize_session_token(session_token)}")
        return conversation_id
    
    def add_message(self, role: str, content: str, conversation_id: str = None, session_token: str = None) -> bool:
        """
        Add a message to a conversation
        
        Args:
            role: "student" or "assistant"
            content: Message content
            conversation_id: Optional conversation ID (uses current session active conversation if not specified)
            session_token: Session token for user isolation
        
        Returns:
            True if successful
        """
        conv_id = conversation_id or self._get_active_conversation_id(session_token)
        
        if not conv_id:
            print("No active conversation")
            return False
        
        file_path = self._get_conversation_file(conv_id, session_token)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            data["messages"].append(message)
            data["updated_at"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            
            return True
        except Exception as e:
            print(f"Error adding message: {e}")
            return False
    
    def add_query_result(self, question: str, answer: str, sources: List[str], 
                        num_context_docs: int, conversation_id: str = None, session_token: str = None) -> bool:
        """
        Add a complete Q&A result to conversation
        
        Args:
            question: The question asked
            answer: The assistant's answer
            sources: List of source documents
            num_context_docs: Number of context documents used
            conversation_id: Optional conversation ID
            session_token: Session token for user isolation
        
        Returns:
            True if successful
        """
        conv_id = conversation_id or self._get_active_conversation_id(session_token)
        
        if not conv_id:
            return False
        
        file_path = self._get_conversation_file(conv_id, session_token)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data["messages"].append({
                "role": "student",
                "content": question,
                "timestamp": datetime.now().isoformat()
            })
            
            data["messages"].append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "context_docs": num_context_docs,
                "timestamp": datetime.now().isoformat()
            })
            
            data["updated_at"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            
            return True
        except Exception as e:
            print(f"Error adding query result: {e}")
            return False
    
    def get_conversation(self, conversation_id: str, session_token: str = None) -> Optional[Dict]:
        """
        Load a conversation by ID for a specific session
        
        Args:
            conversation_id: ID of conversation to load
            session_token: Session token for user isolation
        
        Returns:
            Conversation data or None if not found
        """
        file_path = self._get_conversation_file(conversation_id, session_token)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading conversation: {e}")
            return None
    
    def list_conversations(self, limit: int = None, session_token: str = None) -> List[Dict]:
        """
        List all saved conversations for a specific session
        
        Args:
            limit: Maximum number of conversations to return (most recent first)
            session_token: Session token for user isolation
        
        Returns:
            List of conversation summaries
        """
        conversations = []
        session_dir = self._get_session_dir(session_token)
        
        try:
            for file_path in sorted(session_dir.glob("conv_*.json"), reverse=True):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                summary = {
                    "id": data["id"],
                    "title": data["title"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "message_count": len(data["messages"])
                }
                conversations.append(summary)
                
                if limit and len(conversations) >= limit:
                    break
        except Exception as e:
            print(f"Error listing conversations: {e}")
        
        return conversations
    
    def delete_conversation(self, conversation_id: str, session_token: str = None) -> bool:
        """
        Delete a saved conversation for a session
        
        Args:
            conversation_id: ID of conversation to delete
            session_token: Session token for user isolation
        
        Returns:
            True if successful
        """
        file_path = self._get_conversation_file(conversation_id, session_token)
        
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"Deleted conversation: {conversation_id}")
                
                active_id = self._get_active_conversation_id(session_token)
                if active_id == conversation_id:
                    self._set_active_conversation_id(None, session_token)
                
                return True
            return False
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def set_current_conversation(self, conversation_id: str, session_token: str = None) -> bool:
        """
        Set the active conversation for a session
        
        Args:
            conversation_id: ID of conversation to activate
            session_token: Session token for user isolation
        
        Returns:
            True if successful
        """
        file_path = self._get_conversation_file(conversation_id, session_token)
        
        if not file_path.exists():
            print(f"Conversation not found: {conversation_id}")
            return False
        
        self._set_active_conversation_id(conversation_id, session_token)
        print(f"Loaded conversation: {conversation_id} for session {self._sanitize_session_token(session_token)}")
        return True
    
    def get_current_conversation(self, session_token: str = None) -> Optional[Dict]:
        """Get the current active conversation for a session"""
        conversation_id = self._get_active_conversation_id(session_token)
        if not conversation_id:
            return None
        return self.get_conversation(conversation_id, session_token)
    
    def clear_all_conversations(self, session_token: str = None) -> int:
        """
        Delete all conversations for a specific session
        
        Returns:
            Number of conversations deleted
        """
        count = 0
        session_dir = self._get_session_dir(session_token)
        
        try:
            for file_path in session_dir.glob("conv_*.json"):
                file_path.unlink()
                count += 1
            
            self._set_active_conversation_id(None, session_token)
            print(f"Cleared {count} conversations for session {self._sanitize_session_token(session_token)}")
        except Exception as e:
            print(f"Error clearing conversations: {e}")
        return count


# Global instance
conversation_manager = ConversationManager()
