import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from agent.graph import build_graph
from app.config import SCENARIOS

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    sys.exit(1)

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
app_agent = build_graph(llm)

for label, scenario_id in SCENARIOS.items():
    print(f"\n--- Testing Scenario: {label} ({scenario_id}) ---")
    try:
        res = app_agent.invoke({"user_question": "what is creating the drift?", "scenario": scenario_id})
        evidence = res.get("evidence", "")
        # truncate evidence to show structure
        print("EVIDENCE LENGTH:", len(evidence))
        print("RESPONSE SNIPPET:", res.get("final_response", "")[:200].replace("\n", " ") + "...")
        print("ERRORS:", res.get("errors"))
    except Exception as e:
        print("CRASHED:", e)
