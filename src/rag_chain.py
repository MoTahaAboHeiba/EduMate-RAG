"""
RAG Chain with Conversation Memory - Multi-turn conversations
"""
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from googletrans import Translator
    
from src.config import config
from src.vector_store import vector_store
from src.conversation_manager import conversation_manager
from src.retrieval_optimizer import retrieval_optimizer
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
        self.supported_languages = ['ar', 'en', 'fr', 'es', 'de']  # Add more as needed
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the text
        
        Args:
            text: Text to detect language for
        
        Returns:
            Language code (e.g., 'en', 'ar')
        """
        try:
            result = self.translator.detect(text)
            return result.lang
        except Exception as e:
            print(f"Error detecting language: {e}")
            return 'en'  # Default to English
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source to target language
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
        
        Returns:
            Translated text
        """
        if source_lang == target_lang:
            return text
        
        try:
            result = self.translator.translate(text, src=source_lang, dest=target_lang)
            return result.text
        except Exception as e:
            print(f"Error translating text: {e}")
            return text  # Return original text on error
    
    def is_non_english(self, text: str) -> bool:
        """Check if text is in a non-English language"""
        detected_lang = self.detect_language(text)
        return detected_lang != 'en'


class RAGChain:
    """RAG pipeline with conversation memory: Retrieve + Generate + Remember"""
    
    def __init__(self, max_memory_messages: int = 10):
        """
        Initialize RAG chain with conversation memory
        
        Args:
            max_memory_messages: Number of previous messages to remember
        """
        # Initialize Groq LLM with optimization settings
        # Lower temperature (0.5 vs 0.7) reduces hallucinations
        # Higher max_tokens (1500 vs 1000) increases answer completeness
        self.llm = ChatGroq(
            api_key=config.GROQ_API_KEY,
            model_name=config.GROQ_MODEL,
            temperature=config.LLM_TEMPERATURE,  # Optimized: 0.5 (was 0.7)
            max_tokens=config.LLM_MAX_TOKENS  # Optimized: 1500 (was 1000)
        )
        print(f"[RAGChain] LLM initialized: temperature={config.LLM_TEMPERATURE}, max_tokens={config.LLM_MAX_TOKENS}")
        
        # Initialize conversation memory storage per session
        self.session_memory: Dict[str, SimpleMemory] = {}
        self.session_conversation_ids: Dict[str, str] = {}
        
        # Initialize language helper for translation
        self.language_helper = LanguageHelper()
        
        # Create prompt template with conversation history
        # OPTIMIZATION: Improved instructions to reduce hallucinations and increase completeness
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question", "chat_history"],
            template="""Your name is EduMate. You are a helpful academic assistant for Student.

You are having a conversation with a student about their course materials, be friendly and helpful. You have access to the following course materials to answer the student's questions. Use them to provide accurate and concise answers.
Below is the conversation history so far, followed by relevant course materials and the new question.

=== CONVERSATION HISTORY ===
{chat_history}

=== RELEVANT COURSE MATERIALS ===
{context}

=== NEW QUESTION ===
Student: {question}

IMPORTANT INSTRUCTIONS:
1. **ONLY use information from the provided course materials.** Do not use external knowledge.
2. **Base all claims on the provided materials.** If something is not mentioned, say so explicitly.
3. Provide detailed, comprehensive answers with examples from the materials.
4. Reference previous questions in the conversation if relevant.
5. If the student asks "tell me more", "explain further", or "why", provide additional detail.
6. **If information is NOT in the provided materials, clearly state: "I don't have this information in the course materials"**
7. Be conversational, helpful, and thorough.
8. Structure complex answers with clear sections or bullet points.
9. **Ground every claim with evidence from the materials.**
10. Include relevant page context or section references when possible.

Answer:"""
        )
        
        # Store max memory setting
        self.max_memory = max_memory_messages
        
        # Log Phase 6 enhancements if enabled
        if config.ENFORCE_VALIDATION:
            print(f"[RAGChain] Phase 6 Enforcement: ENABLED (grounding threshold: {config.GROUNDING_THRESHOLD:.0%})")
        if config.ENABLE_SIMILARITY_FILTERING:
            print(f"[RAGChain] Similarity Filtering: ENABLED (threshold: {config.SIMILARITY_THRESHOLD:.1f})")
    
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

    def _validate_answer_grounding(self, answer: str, context: str) -> tuple[bool, float]:
        """
        OPTIMIZATION: Validate if answer is grounded in retrieved context.
        This helps detect hallucinations where LLM generates information not in context.
        
        Args:
            answer: Generated answer
            context: Retrieved context from documents
        
        Returns:
            Tuple of (is_grounded: bool, confidence: float 0-1)
        """
        if not context or not answer:
            return True, 1.0  # Can't validate, assume OK
        
        # Simple validation: Check if key phrases from answer appear in context
        # Split answer into key phrases (sentences/chunks)
        answer_sentences = [s.strip() for s in answer.split('.') if s.strip() and len(s.split()) > 3]
        
        if not answer_sentences:
            return True, 1.0
        
        # Check what percentage of answer sentences are grounded in context
        grounded_count = 0
        for sentence in answer_sentences:
            # Check if sentence (or parts of it) appear in context
            # Use key words from sentence
            words = [w.lower() for w in sentence.split() if len(w) > 4]  # Focus on longer words
            
            if any(word in context.lower() for word in words[:3]):  # Check first 3 key words
                grounded_count += 1
        
        if not answer_sentences:
            return True, 1.0
        
        grounding_score = grounded_count / len(answer_sentences)
        is_grounded = grounding_score >= 0.6  # Require 60% grounding
        
        if config.ENABLE_RETRIEVAL_VALIDATION and not is_grounded:
            print(f"   [VALIDATION] Answer grounding score: {grounding_score:.1%} (threshold: {config.GROUNDING_THRESHOLD:.0%})")
            return False, grounding_score
        
        return True, grounding_score

    def query(self, question: str, session_token: str = None, num_context_docs: int = 3) -> dict:
        """
        Query the RAG system with conversation memory for a specific session
        
        Args:
            question: Student's question
            session_token: Session token for user isolation
            num_context_docs: Number of relevant documents to retrieve
        
        Returns:
            Dictionary with answer, sources, and conversation context
        """
        print(f"\n Processing question: {question}")
        
        token = self._normalize_session_token(session_token)
        memory = self._get_memory(token)
        current_conversation_id = self._get_conversation_id(token)
        
        # Detect language and translate if necessary
        detected_lang = self.language_helper.detect_language(question)
        print(f"   Detected language: {detected_lang}")
        
        # Translate question to English for retrieval if it's not English
        search_question = question
        if detected_lang != 'en':
            search_question = self.language_helper.translate_text(question, detected_lang, 'en')
            print(f"   Translated question to English: {search_question}")
        
        # Get conversation history
        chat_history = memory.buffer
        
        # Check if this is a general question (doesn't need course materials)
        is_general_question = self._is_general_question(question)
        
        if is_general_question:
            print("   General question detected - skipping document retrieval")
            retrieved_docs = []
            context = ""
        else:
            print("   Retrieving relevant documents...")
            # OPTIMIZATION: Retrieve more documents (5 instead of 3) to reduce precision gap
            # Will filter to top-3 based on relevance and reranking if enabled
            retrieve_k = min(config.RETRIEVAL_TOP_K, max(num_context_docs + 2, 5))  # Retrieve at least 5
            raw_docs = vector_store.search(search_question, num_results=retrieve_k)
            
            if not raw_docs:
                print("   No relevant documents found")
                retrieved_docs = []
                context = ""
            else:
                print(f"   Found {len(raw_docs)} raw documents from vector store")
                
                # OPTIMIZATION: Apply optimization pipeline to improve precision
                # This includes filtering, reranking, deduplication
                retrieved_docs = retrieval_optimizer.optimize_retrieval(
                    raw_docs,
                    query=search_question,
                    top_k=num_context_docs,  # Return only top_k for context
                    enable_dedup=True,
                    enable_rerank=True,
                    similarity_threshold=config.RETRIEVAL_SIMILARITY_THRESHOLD
                )
                
                print(f"   After optimization: {len(retrieved_docs)} documents selected for context")
                
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
            
            # OPTIMIZATION: Validate answer grounding if retrieval validation enabled
            if retrieved_docs and config.ENABLE_RETRIEVAL_VALIDATION:
                is_grounded, grounding_score = self._validate_answer_grounding(answer, context)
                if not is_grounded:
                    print(f"   [VALIDATION WARNING] Answer may contain hallucinations (grounding: {grounding_score:.1%})")
                    # Phase 6: Enforce validation - reject ungrounded answers
                    if config.ENFORCE_VALIDATION:
                        print(f"   [PHASE 6 ENFORCEMENT] Rejecting answer - grounding {grounding_score:.1%} below threshold {config.GROUNDING_THRESHOLD:.0%}")
                        answer = "I don't have enough information in the course materials to answer this question confidently. Please try rephrasing or ask about a different topic."
                        print(f"   [FALLBACK] Using safe response instead")
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
        """
        Detect if a question is general and doesn't require course materials
        (e.g., greetings, meta questions about the AI itself)
        
        Args:
            question: The question to check
        
        Returns:
            True if it's a general question, False otherwise
        """
        question_lower = question.lower().strip()
        
        # List of patterns for general questions
        general_patterns = [
            # Greetings
            'hello', 'hi ', 'hey ', 'greetings', 'howdy',
            # Personal/Meta questions about the AI
            'who are you', "what's your name", 'what is your name', 'your name', 'tell me about yourself',
            'what can you do', 'how can you help', 'what are your capabilities',
            'how are you', "how're you",
            # Casual questions
            'nice to meet you', 'glad to meet you',
            # Help questions
            'can you help me', 'please help', 'help me',
            # General pleasantries
            'thank you', 'thanks', 'appreciate', "thank's", 'thank u',
        ]
        
        # Check if question matches any general pattern
        for pattern in general_patterns:
            if pattern in question_lower:
                return True
        
        return False
    
    def get_conversation_history(self, session_token: str = None) -> List[Dict]:
        """Get the current conversation history for a session"""
        history = []
        memory = self._get_memory(self._normalize_session_token(session_token))
        buffer_text = memory.buffer
        
        lines = buffer_text.split('\n')
        for line in lines:
            if line.strip().startswith('Student:'):
                history.append({
                    "role": "student",
                    "content": line.replace('Student:', '').strip()
                })
            elif line.strip().startswith('Assistant:'):
                history.append({
                    "role": "assistant",
                    "content": line.replace('Assistant:', '').strip()
                })
        
        return history
    
    def clear_memory(self, session_token: str = None):
        """Clear conversation memory (start fresh conversation) for a session"""
        memory = self._get_memory(self._normalize_session_token(session_token))
        memory.clear()
        self._set_conversation_id(None, self._normalize_session_token(session_token))
        print(f"Conversation memory cleared for session {self._normalize_session_token(session_token)}")
    
    def start_new_conversation(self, session_token: str = None, title: str = None) -> str:
        """
        Start a new conversation and save it for a session
        
        Args:
            session_token: Session token for user isolation
            title: Optional title for the conversation
        
        Returns:
            Conversation ID
        """
        token = self._normalize_session_token(session_token)
        memory = self._get_memory(token)
        memory.clear()
        
        conversation_id = conversation_manager.create_conversation(title, session_token=token)
        self._set_conversation_id(conversation_id, token)
        print(f"Started new conversation: {conversation_id} for session {token}")
        
        return conversation_id
    
    def load_conversation(self, conversation_id: str, session_token: str = None) -> bool:
        """
        Load a saved conversation for a session
        
        Args:
            conversation_id: ID of conversation to load
            session_token: Session token for user isolation
        
        Returns:
            True if successful
        """
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
        """
        List all saved conversations for a session
        
        Args:
            limit: Maximum number to return
            session_token: Session token for user isolation
        
        Returns:
            List of conversation summaries
        """
        return conversation_manager.list_conversations(limit=limit, session_token=self._normalize_session_token(session_token))
    
    def get_current_conversation_id(self, session_token: str = None) -> str:
        """Get the current conversation ID for a session"""
        return self._get_conversation_id(self._normalize_session_token(session_token))
    
    def delete_conversation(self, conversation_id: str, session_token: str = None) -> bool:
        """
        Delete a saved conversation for a session
        
        Args:
            conversation_id: ID to delete
            session_token: Session token for user isolation
        
        Returns:
            True if successful
        """
        return conversation_manager.delete_conversation(conversation_id, session_token=self._normalize_session_token(session_token))
    
    def get_memory_summary(self, session_token: str = None) -> dict:
        """Get summary of current conversation for a session"""
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
