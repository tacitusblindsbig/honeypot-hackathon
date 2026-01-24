from typing import List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict, constr


NonEmptyStr = constr(min_length=1, strip_whitespace=True)


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: Literal["scammer"] = Field(..., description="Sender must be 'scammer'.")
    text: NonEmptyStr
    timestamp: NonEmptyStr


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: NonEmptyStr
    text: NonEmptyStr
    timestamp: NonEmptyStr


class Metadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    channel: NonEmptyStr
    language: NonEmptyStr
    locale: NonEmptyStr


class HoneyPotRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sessionId: NonEmptyStr
    message: Message
    conversationHistory: Optional[List[ConversationMessage]] = None
    metadata: Optional[Metadata] = None


class EngagementMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    engagementDurationSeconds: int
    totalMessagesExchanged: int


class ExtractedIntelligence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bankAccounts: List[str]
    upiIds: List[str]
    phishingLinks: List[str]
    phoneNumbers: List[str]
    suspiciousKeywords: List[str]


class HoneyPotResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["success"]
    scamDetected: bool
    engagementMetrics: EngagementMetrics
    extractedIntelligence: ExtractedIntelligence
    agentNotes: NonEmptyStr
    reply: Optional[NonEmptyStr] = None
