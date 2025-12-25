from langchain_groq import ChatGroq
from src.config import config

# Test Groq connection
try:
    llm = ChatGroq(
        api_key=config.GROQ_API_KEY,
        model_name=config.GROQ_MODEL,
        temperature=0.7,
        max_tokens=1000
    )
    
    print("Testing Groq connection...")
    response = llm.invoke("What is a prerequisite in university?")
    print("Groq is working!")
    print(f"Response: {response}")

except Exception as e:
    print(f"Groq Error: {e}")

