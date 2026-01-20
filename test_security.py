import os
from dotenv import load_dotenv, find_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(find_dotenv())

# 1. Check Env Variable
provider = os.getenv("MODEL_PROVIDER", "Not Set")
print(f"1. .env Variable says: {provider}")

# 2. Try to Connect to Groq directly
try:
    print("\n2. Testing Groq Connection...")
    groq_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )
    response = groq_llm.invoke("Who created you? Answer in 1 sentence.")
    print(f"✅ GROQ RESPONSE: {response.content}")
    # Expect: "I am Llama 3, created by Meta." (Groq hosts Llama models)
except Exception as e:
    print(f"❌ GROQ FAILED: {e}")

# 3. Try to Connect to Gemini directly
try:
    print("\n3. Testing Gemini Connection...")
    gemini_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    response = gemini_llm.invoke("Who created you? Answer in 1 sentence.")
    print(f"✅ GEMINI RESPONSE: {response.content}")
    # Expect: "I am a large language model, trained by Google."
except Exception as e:
    print(f"❌ GEMINI FAILED: {e}")