from typing import List, Optional, Literal

from pydantic import BaseModel, Field, constr


NonEmptyStr = constr(min_length=1, strip_whitespace=True)


class Message(BaseModel):
    sender: Literal["scammer"] = Field(..., description="Sender must be 'scammer'.")
    text: NonEmptyStr
    timestamp: NonEmptyStr

    class Config:
        extra = "forbid"


class ConversationMessage(BaseModel):
    sender: NonEmptyStr
    text: NonEmptyStr
    timestamp: NonEmptyStr

    class Config:
        extra = "forbid"


class Metadata(BaseModel):
    channel: NonEmptyStr
    language: NonEmptyStr
    locale: NonEmptyStr

    class Config:
        extra = "forbid"


class HoneyPotRequest(BaseModel):
    sessionId: NonEmptyStr
    message: Message
    conversationHistory: List[ConversationMessage]
    metadata: Metadata

    class Config:
        extra = "forbid"


class EngagementMetrics(BaseModel):
    engagementDurationSeconds: int
    totalMessagesExchanged: int

    class Config:
        extra = "forbid"


class ExtractedIntelligence(BaseModel):
    bankAccounts: List[str]
    upiIds: List[str]
    phishingLinks: List[str]
    phoneNumbers: List[str]
    suspiciousKeywords: List[str]

    class Config:
        extra = "forbid"


class HoneyPotResponse(BaseModel):
    status: Literal["success"]
    scamDetected: bool
    engagementMetrics: EngagementMetrics
    extractedIntelligence: ExtractedIntelligence
    agentNotes: NonEmptyStr
    reply: Optional[NonEmptyStr] = None

    class Config:
        extra = "forbid"
