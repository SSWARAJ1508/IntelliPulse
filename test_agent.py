import os
import sys
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from agent.graph import build_graph

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("No API key set in .env")
    sys.exit(1)

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
app_agent = build_graph(llm)

try:
    res = app_agent.invoke({"user_question": "what is causing the data drift?", "scenario": "stable"})
    print("FINAL RESPONSE:")
    print(res.get("final_response"))
    print("\nERRORS:")
    print(res.get("errors"))
except Exception as e:
    print("CRASHED:", e)
