"""
RAG Chain with Conversation Memory - Multi-turn conversations
"""
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from googletrans import Translator
from src.config.config import config
from src.document_processing.vector_store import vector_store
from src.conversation.conversation_manager import conversation_manager
from src.core.retrieval_optimizer import retrieval_optimizer
from typing import List, Dict


class SimpleMemory:
    """Simple conversation memory buffer"""
    def __init__(self):
        self.buffer = ""
    
    def save_context(self, inputs, outputs):
        """Add Q&A pair to memory"""
        question = inputs.get("input", "")
        answer = outputs.get("output", "")
        self.buffer += f"Student: {question}\nAssistant: {answer}\n\n"
    
    def clear(self):
        """Clear memory"""
        self.buffer = ""


class LanguageHelper:
    """Helper class for detecting and translating languages"""
    
    def __init__(self):
        self.translator = Translator()
        self.supported_languages = ['ar', 'en', 'fr', 'es', 'de']
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the text"""
        try:
            result = self.translator.detect(text)
            return result.lang
        except Exception as e:
            print(f"Error detecting language: {e}")
            return 'en'
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text from source to target language"""
        if source_lang == target_lang:
            return text
        
        try:
            result = self.translator.translate(text, src=source_lang, dest=target_lang)
            return result.text
        except Exception as e:
            print(f"Error translating text: {e}")
            return text
    
    def is_non_english(self, text: str) -> bool:
        """Check if text is in a non-English language"""
        detected_lang = self.detect_language(text)
        return detected_lang != 'en'


class RAGChain:
    """RAG pipeline with conversation memory"""
    
    def __init__(self, max_memory_messages: int = 10):
        """Initialize RAG chain with conversation memory"""
        self.llm = ChatGroq(
            api_key=config.GROQ_API_KEY,
            model_name=config.GROQ_MODEL,
            temperature=0.7,
            max_tokens=1000
        )
        
        self.session_memory: Dict[str, SimpleMemory] = {}
        self.session_conversation_ids: Dict[str, str] = {}
        self.language_helper = LanguageHelper()
        
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question", "chat_history"],
            template="""Your name is EduMate. You are a helpful academic assistant for Student.

You are having a conversation with a student about their course materials. Use them to provide accurate answers.
Below is the conversation history, followed by relevant course materials and the new question.

=== CONVERSATION HISTORY ===
{chat_history}

=== RELEVANT COURSE MATERIALS ===
{context}

=== NEW QUESTION ===
Student: {question}

IMPORTANT: Use only information from the provided materials. If not available, say so clearly.

Answer:"""
        )
        
        self.max_memory = max_memory_messages
    
    def _normalize_session_token(self, session_token: str) -> str:
        return session_token or 'anonymous'

    def _get_memory(self, session_token: str) -> SimpleMemory:
        token = self._normalize_session_token(session_token)
        if token not in self.session_memory:
            self.session_memory[token] = SimpleMemory()
        return self.session_memory[token]

    def _get_conversation_id(self, session_token: str) -> str:
        token = self._normalize_session_token(session_token)
        return self.session_conversation_ids.get(token)

    def _set_conversation_id(self, conversation_id: str, session_token: str):
        token = self._normalize_session_token(session_token)
        self.session_conversation_ids[token] = conversation_id

    def query(self, question: str, session_token: str = None, num_context_docs: int = 3) -> dict:
        """Query the RAG system"""
        print(f"\n Processing question: {question}")
        
        token = self._normalize_session_token(session_token)
        memory = self._get_memory(token)
        current_conversation_id = self._get_conversation_id(token)
        
        detected_lang = self.language_helper.detect_language(question)
        print(f"   Detected language: {detected_lang}")
        
        search_question = question
        if detected_lang != 'en':
            search_question = self.language_helper.translate_text(question, detected_lang, 'en')
            print(f"   Translated question to English: {search_question}")
        
        chat_history = memory.buffer
        is_general_question = self._is_general_question(question)
        
        if is_general_question:
            print("   General question detected - skipping document retrieval")
            retrieved_docs = []
            context = ""
        else:
            print("   Retrieving relevant documents...")
            retrieved_docs = vector_store.search(search_question, num_results=num_context_docs)
            
            if not retrieved_docs:
                print("   No relevant documents found")
                context = ""
            else:
                print(f"   Found {len(retrieved_docs)} relevant documents")
                context = "\n\n---\n\n".join([
                    f"[{doc['metadata']['source']}] {doc['content']}"
                    for doc in retrieved_docs
                ])
        
        print("   Generating answer with Groq...")
        try:
            prompt_input = self.prompt_template.format(
                context=context,
                question=question,
                chat_history=chat_history
            )
            response = self.llm.invoke(prompt_input)
            answer = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        except Exception as e:
            print(f"   Error generating answer: {e}")
            answer = ""
        
        if detected_lang != 'en':
            answer = self.language_helper.translate_text(answer, 'en', detected_lang)
            print(f"   Translated answer back to {detected_lang}")
        
        memory.save_context({"input": question}, {"output": answer})
        
        buffer_text = memory.buffer
        conversation_turn = buffer_text.count('Student:')
        
        if not current_conversation_id and conversation_turn == 1:
            current_conversation_id = conversation_manager.create_conversation("Auto-generated Conversation", session_token=token)
            self._set_conversation_id(current_conversation_id, token)
            print(f"   Auto-created conversation: {current_conversation_id}")
        
        if current_conversation_id:
            conversation_manager.add_query_result(
                question=question,
                answer=answer,
                sources=[doc['metadata']['source'] for doc in retrieved_docs] if retrieved_docs else [],
                num_context_docs=len(retrieved_docs),
                conversation_id=current_conversation_id,
                session_token=token
            )
            self._set_conversation_id(current_conversation_id, token)
        
        result = {
            "question": question,
            "answer": answer,
            "sources": list(set([doc['metadata']['source'] for doc in retrieved_docs])) if retrieved_docs else [],
            "num_context_docs": len(retrieved_docs),
            "conversation_turn": conversation_turn,
            "conversation_id": current_conversation_id,
            "is_general": is_general_question
        }
        
        print(f"   Answer generated (Turn {conversation_turn})")
        return result
    
    def _is_general_question(self, question: str) -> bool:
        """Detect if a question is general"""
        question_lower = question.lower().strip()
        
        general_patterns = [
            'hello', 'hi ', 'hey ', 'greetings', 'howdy',
            'who are you', "what's your name", 'your name',
            'how are you', "how're you",
            'thank you', 'thanks',
        ]
        
        for pattern in general_patterns:
            if pattern in question_lower:
                return True
        
        return False
    
    def get_conversation_history(self, session_token: str = None) -> List[Dict]:
        """Get conversation history"""
        history = []
        memory = self._get_memory(self._normalize_session_token(session_token))
        buffer_text = memory.buffer
        
        lines = buffer_text.split('\n')
        for line in lines:
            if line.strip().startswith('Student:'):
                history.append({"role": "student", "content": line.replace('Student:', '').strip()})
            elif line.strip().startswith('Assistant:'):
                history.append({"role": "assistant", "content": line.replace('Assistant:', '').strip()})
        
        return history
    
    def clear_memory(self, session_token: str = None):
        """Clear conversation memory"""
        memory = self._get_memory(self._normalize_session_token(session_token))
        memory.clear()
        self._set_conversation_id(None, self._normalize_session_token(session_token))
        print(f"Conversation memory cleared for session {self._normalize_session_token(session_token)}")
    
    def start_new_conversation(self, session_token: str = None, title: str = None) -> str:
        """Start a new conversation"""
        token = self._normalize_session_token(session_token)
        memory = self._get_memory(token)
        memory.clear()
        
        conversation_id = conversation_manager.create_conversation(title, session_token=token)
        self._set_conversation_id(conversation_id, token)
        print(f"Started new conversation: {conversation_id} for session {token}")
        
        return conversation_id
    
    def load_conversation(self, conversation_id: str, session_token: str = None) -> bool:
        """Load a saved conversation"""
        token = self._normalize_session_token(session_token)
        conv_data = conversation_manager.get_conversation(conversation_id, session_token=token)
        
        if not conv_data:
            print(f"Conversation not found: {conversation_id}")
            return False
        
        memory = self._get_memory(token)
        memory.clear()
        
        messages = conv_data.get("messages", [])
        
        if messages:
            for i in range(0, len(messages), 2):
                student_msg = messages[i] if i < len(messages) else None
                assistant_msg = messages[i + 1] if i + 1 < len(messages) else None
                
                if student_msg and assistant_msg:
                    memory.save_context(
                        {"input": student_msg.get("content", "")},
                        {"output": assistant_msg.get("content", "")}
                    )
                elif student_msg:
                    memory.save_context(
                        {"input": student_msg.get("content", "")},
                        {"output": ""}
                    )
        
        self._set_conversation_id(conversation_id, token)
        conversation_manager.set_current_conversation(conversation_id, session_token=token)
        print(f"Loaded conversation: {conversation_id} ({len(messages)} messages) for session {token}")
        
        return True
    
    def list_saved_conversations(self, limit: int = 10, session_token: str = None) -> List[Dict]:
        """List saved conversations"""
        return conversation_manager.list_conversations(limit=limit, session_token=self._normalize_session_token(session_token))
    
    def get_current_conversation_id(self, session_token: str = None) -> str:
        """Get current conversation ID"""
        return self._get_conversation_id(self._normalize_session_token(session_token))
    
    def delete_conversation(self, conversation_id: str, session_token: str = None) -> bool:
        """Delete a conversation"""
        return conversation_manager.delete_conversation(conversation_id, session_token=self._normalize_session_token(session_token))
    
    def get_memory_summary(self, session_token: str = None) -> dict:
        """Get memory summary"""
        memory = self._get_memory(self._normalize_session_token(session_token))
        buffer_text = memory.buffer
        
        student_count = buffer_text.count('Student:')
        assistant_count = buffer_text.count('Assistant:')
        
        return {
            "total_turns": max(student_count, assistant_count),
            "total_messages": student_count + assistant_count,
            "messages": buffer_text[:500] + "..." if len(buffer_text) > 500 else buffer_text
        }


# Global instance
rag_chain = RAGChain()
