"""
RAG Chain - Retrieval-Augmented Generation pipeline
"""
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from src.config import config
from src.vector_store import vector_store

class RAGChain:
    """RAG pipeline: Retrieve documents + Generate answer"""
    
    def __init__(self):
        """Initialize RAG chain"""
        # Initialize Groq LLM
        self.llm = ChatGroq(
            api_key=config.GROQ_API_KEY,
            model_name=config.GROQ_MODEL,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Create prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a helpful academic assistant for EduMate.
            
Use the following course materials to answer the question.
If the information is not in the provided materials, say "I don't have this information in the course materials."

Course Materials:
{context}

Student Question: {question}

Answer:"""
        )
        
        # Create chain
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
    
    def query(self, question: str, num_context_docs: int = 3) -> dict:
        """
        Query the RAG system
        
        Args:
            question: Student's question
            num_context_docs: Number of relevant documents to retrieve
        
        Returns:
            Dictionary with answer and sources
        """
        print(f"\n🔍 Processing question: {question}")
        
        # Step 1: Retrieve relevant documents
        print("   📚 Retrieving relevant documents...")
        retrieved_docs = vector_store.search(question, num_results=num_context_docs)
        
        if not retrieved_docs:
            return {
                "question": question,
                "answer": "I couldn't find relevant course materials to answer this question.",
                "sources": []
            }
        
        print(f"   ✅ Found {len(retrieved_docs)} relevant documents")
        
        # Step 2: Prepare context
        context = "\n\n---\n\n".join([
            f"[{doc['metadata']['source']}] {doc['content']}"
            for doc in retrieved_docs
        ])
        
        # Step 3: Generate answer
        print("   🤖 Generating answer with Groq...")
        try:
            answer = self.chain.run(context=context, question=question)
            answer = answer.strip()
        except Exception as e:
            print(f"   ❌ Error generating answer: {e}")
            answer = "An error occurred while generating the answer."
        
        # Step 4: Prepare sources
        sources = list(set([doc['metadata']['source'] for doc in retrieved_docs]))
        
        result = {
            "question": question,
            "answer": answer,
            "sources": sources,
            "num_context_docs": len(retrieved_docs)
        }
        
        print(f"   ✅ Answer generated from: {', '.join(sources)}")
        return result


# Global instance
rag_chain = RAGChain()
