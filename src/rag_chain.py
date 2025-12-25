"""
RAG Chain with Conversation Memory - Multi-turn conversations
"""
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from src.config import config
from src.vector_store import vector_store
from typing import List, Dict

class RAGChain:
    """RAG pipeline with conversation memory: Retrieve + Generate + Remember"""
    
    def __init__(self, max_memory_messages: int = 10):
        """
        Initialize RAG chain with conversation memory
        
        Args:
            max_memory_messages: Number of previous messages to remember
        """
        # Initialize Groq LLM
        self.llm = ChatGroq(
            api_key=config.GROQ_API_KEY,
            model_name=config.GROQ_MODEL,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=False,
            human_prefix="Student",
            ai_prefix="Assistant"
        )
        
        # Create prompt template with conversation history
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question", "chat_history"],
            template="""You are a helpful academic assistant for EduMate.

You are having a conversation with a student about their course materials.
Below is the conversation history so far, followed by relevant course materials and the new question.

=== CONVERSATION HISTORY ===
{chat_history}

=== RELEVANT COURSE MATERIALS ===
{context}

=== NEW QUESTION ===
Student: {question}

IMPORTANT INSTRUCTIONS:
1. Use the course materials to answer accurately
2. Reference previous questions in the conversation if relevant
3. If the student asks "tell me more", "explain further", or "why", refer to your previous answer
4. If information is not in the provided materials, say "I don't have this information in the course materials"
5. Be conversational and helpful
6. Keep your answers concise but complete

Answer:"""
        )
        
        # Create chain
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
        self.max_memory = max_memory_messages
    
    def query(self, question: str, num_context_docs: int = 3) -> dict:
        """
        Query the RAG system with conversation memory
        
        Args:
            question: Student's question
            num_context_docs: Number of relevant documents to retrieve
        
        Returns:
            Dictionary with answer, sources, and conversation context
        """
        print(f"\n🔍 Processing question: {question}")
        
        # Get conversation history
        chat_history = self.memory.buffer if hasattr(self.memory, 'buffer') else ""
        
        # Step 1: Retrieve relevant documents
        print("   📚 Retrieving relevant documents...")
        retrieved_docs = vector_store.search(question, num_results=num_context_docs)
        
        if not retrieved_docs:
            answer = "I couldn't find relevant course materials to answer this question."
            sources = []
        else:
            print(f" Found {len(retrieved_docs)} relevant documents")
            
            # Step 2: Prepare context
            context = "\n\n---\n\n".join([
                f"[{doc['metadata']['source']}] {doc['content']}"
                for doc in retrieved_docs
            ])
            
            # Step 3: Generate answer with conversation history
            print(" Generating answer with Groq...")
            try:
                answer = self.chain.run(
                    context=context,
                    question=question,
                    chat_history=chat_history
                )
                answer = str(answer).strip()
            except Exception as e:
                print(f" Error generating answer: {e}")
                answer = f"Error: {str(e)}"
            
            # Step 4: Prepare sources
            sources = list(set([doc['metadata']['source'] for doc in retrieved_docs]))
        
        # Step 5: Save to memory for next conversation
        self.memory.save_context(
            {"input": question},
            {"output": answer}
        )
        
        # Count turns
        buffer_text = self.memory.buffer if hasattr(self.memory, 'buffer') else ""
        conversation_turn = buffer_text.count('Student:')
        
        result = {
            "question": question,
            "answer": answer,
            "sources": sources,
            "num_context_docs": len(retrieved_docs),
            "conversation_turn": conversation_turn
        }
        
        print(f" Answer generated (Turn {conversation_turn})")
        return result
    
    def get_conversation_history(self) -> List[Dict]:
        """Get the current conversation history"""
        history = []
        
        # Get buffer from memory
        buffer_text = self.memory.buffer if hasattr(self.memory, 'buffer') else ""
        
        # Parse the conversation from buffer
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
    
    def clear_memory(self):
        """Clear conversation memory (start fresh conversation)"""
        self.memory.clear()
        print(" Conversation memory cleared")
    
    def get_memory_summary(self) -> dict:
        """Get summary of current conversation"""
        buffer_text = self.memory.buffer if hasattr(self.memory, 'buffer') else ""
        
        # Count turns
        student_count = buffer_text.count('Student:')
        assistant_count = buffer_text.count('Assistant:')
        
        return {
            "total_turns": max(student_count, assistant_count),
            "total_messages": student_count + assistant_count,
            "messages": buffer_text[:500] + "..." if len(buffer_text) > 500 else buffer_text
        }


# Global instance
rag_chain = RAGChain()
