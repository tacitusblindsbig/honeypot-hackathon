from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# 1. Metrics Schema
class EngagementMetrics(BaseModel):
    engagementDurationSeconds: int
    totalMessagesExchanged: int
    model_config = ConfigDict(extra='ignore')

# 2. Intelligence Schema
class ExtractedIntelligence(BaseModel):
    bankAccounts: List[str] = []
    upiIds: List[str] = []
    phishingLinks: List[str] = []
    phoneNumbers: List[str] = []
    suspiciousKeywords: List[str] = []
    model_config = ConfigDict(extra='ignore')

# 3. The Main Response Schema (This was missing!)
class HoneypotResponse(BaseModel):
    status: str
    scamDetected: bool
    engagementMetrics: EngagementMetrics
    extractedIntelligence: ExtractedIntelligence
    agentNotes: Optional[str] = "Scam detected."
    reply: Optional[str] = "Processing..."
    model_config = ConfigDict(extra='ignore')