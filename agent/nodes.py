from agent.state import AgentState
from agent.schemas import IntentClassification, Intent, StructuredResponse
from agent.prompts import SYSTEM_PROMPT
from agent.tools import (get_latest_health, get_drift_results, get_feature_drift, 
                         get_performance_results, get_monitoring_summary, get_batch_info)

def classify_question(state: AgentState, llm):
    """Classify user intent using LLM structured output"""
    question = state["user_question"]
    
    # Check for security violations first (simple heuristic)
    lower_q = question.lower()
    if any(x in lower_q for x in ["delete", "drop", "insert", "update", "retrain", "change threshold"]):
        return {"intent": Intent.SECURITY_VIOLATION}
        
    structured_llm = llm.with_structured_output(IntentClassification)
    prompt = f"Classify the following monitoring question into an intent:\nQuestion: {question}"
    try:
        res = structured_llm.invoke(prompt)
        return {"intent": res.intent}
    except Exception as e:
        return {"intent": Intent.GENERAL_MONITORING, "errors": [str(e)]}

def retrieve_monitoring_context(state: AgentState):
    """Call appropriate tools based on intent and active batch/scenario"""
    import json
    
    intent = state.get("intent")
    scenario = state.get("scenario")
    batch_id = state.get("batch_id")
    evidence = []
    
    def safe_dump(obj):
        return json.dumps(obj, default=str, indent=2)
    
    if intent == Intent.SECURITY_VIOLATION:
        return {"evidence": "SECURITY_VIOLATION"}

    # If an uploaded batch is targeted, include its batch registry info
    if batch_id:
        batch_meta = get_batch_info.invoke({"batch_id": batch_id})
        evidence.append(f"Batch Metadata:\n{safe_dump(batch_meta)}")
        
    if intent in [Intent.OVERALL_HEALTH, Intent.GENERAL_MONITORING]:
        health = get_latest_health.invoke({"scenario": scenario, "batch_id": batch_id})
        summary = get_monitoring_summary.invoke({"scenario": scenario, "batch_id": batch_id})
        evidence.append(f"Health Assessments:\n{safe_dump(health)}")
        evidence.append(f"Summary:\n{safe_dump(summary)}")
        
    elif intent == Intent.DATA_DRIFT:
        drift = get_drift_results.invoke({"scenario": scenario, "batch_id": batch_id})
        feat_drift = get_feature_drift.invoke({"scenario": scenario, "batch_id": batch_id})
        evidence.append(f"Batch Drift Summary:\n{safe_dump(drift)}")
        evidence.append(f"Feature Drift (Top Drifted):\n{safe_dump(feat_drift)}")
        
    elif intent == Intent.FEATURE_DRIFT:
        feat_drift = get_feature_drift.invoke({"scenario": scenario, "batch_id": batch_id})
        drift = get_drift_results.invoke({"scenario": scenario, "batch_id": batch_id})
        evidence.append(f"Feature Drift:\n{safe_dump(feat_drift)}")
        evidence.append(f"Batch Drift:\n{safe_dump(drift)}")
        
    elif intent in [Intent.MODEL_PERFORMANCE, Intent.PERFORMANCE_COMPARISON]:
        perf = get_performance_results.invoke({"scenario": scenario, "batch_id": batch_id})
        evidence.append(f"Performance Results:\n{safe_dump(perf)}")
        
    elif intent == Intent.RECOMMENDATION:
        health = get_latest_health.invoke({"scenario": scenario, "batch_id": batch_id})
        evidence.append(f"Health Assessments:\n{safe_dump(health)}")
        
    return {"evidence": "\n\n".join(evidence)}

def generate_response(state: AgentState, llm):
    """Generate markdown response based on evidence directly."""
    if state.get("intent") == Intent.SECURITY_VIOLATION:
        return {"final_response": "I am a read-only monitoring assistant. I cannot execute modifying commands, alter the database, change thresholds, or retrain the model."}
        
    prompt = f"""{SYSTEM_PROMPT}

You are the IntelliPulse AI Assistant. Your task is to explain the monitoring results to the user.
Use the retrieved evidence to answer their question. Be conversational but factual.
If the evidence is empty or missing, state that clearly.
Do NOT output JSON. Output your response as a well-formatted Markdown string.

USER QUESTION: {state.get("user_question")}
CLASSIFIED INTENT: {state.get("intent")}
SELECTED SCENARIO: {state.get("scenario")}
ACTIVE BATCH ID: {state.get("batch_id", "None")}

RETRIEVED EVIDENCE:
{state.get("evidence")}
"""
    try:
        res = llm.invoke(prompt)
        content = res.content
        
        # Handle cases where model returns a multimodal content list
        if isinstance(content, list):
            content = " ".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        elif not isinstance(content, str):
            content = str(content)
            
        # Clean up accidental markdown JSON wrapper if the LLM hallucinated JSON anyway
        import re
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            import json
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict):
                    final_str = ""
                    for k, v in data.items():
                        if isinstance(v, list):
                            final_str += f"**{k.title()}:**\n" + "\n".join([f"- {x}" for x in v]) + "\n\n"
                        else:
                            final_str += f"**{k.title()}:** {v}\n\n"
                    return {"final_response": final_str.strip()}
            except Exception:
                pass
                
        return {"final_response": content}
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
            msg = "Gemini API quota exceeded. Please try again later or check your API usage limits."
        elif "404" in err_str or "not found" in err_str:
            msg = "The specified Gemini model was not found."
        elif "auth" in err_str or "api key" in err_str or "403" in err_str or "401" in err_str:
            msg = "Gemini API authentication failed. Please verify your API key."
        else:
            msg = "The AI encountered an error generating a response due to a network or API issue."
        return {"final_response": msg, "errors": [str(e)]}
