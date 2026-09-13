from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class Intent(str, Enum):
    OVERALL_HEALTH = "OVERALL_HEALTH"
    DATA_DRIFT = "DATA_DRIFT"
    MODEL_PERFORMANCE = "MODEL_PERFORMANCE"
    FEATURE_DRIFT = "FEATURE_DRIFT"
    PERFORMANCE_COMPARISON = "PERFORMANCE_COMPARISON"
    RECOMMENDATION = "RECOMMENDATION"
    GENERAL_MONITORING = "GENERAL_MONITORING"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"

class IntentClassification(BaseModel):
    intent: Intent = Field(..., description="The classified intent of the user question")

class StructuredResponse(BaseModel):
    intent: Intent
    status: str
    key_findings: List[str]
    evidence: List[str]
    explanation: str
    recommendation: str
    limitations: List[str]
