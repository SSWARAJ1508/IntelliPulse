from typing import TypedDict, Optional, List, Dict, Any
from agent.schemas import Intent

class AgentState(TypedDict):
    user_question: str
    scenario: Optional[str]
    batch_id: Optional[str]
    intent: Optional[Intent]
    monitoring_context: List[Dict[str, Any]]
    drift_context: List[Dict[str, Any]]
    performance_context: List[Dict[str, Any]]
    health_context: List[Dict[str, Any]]
    evidence: str
    explanation: str
    recommendation: str
    final_response: str
    structured_output: Optional[dict]
    errors: List[str]
