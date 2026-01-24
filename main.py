from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from config import HONEYPOT_API_KEY
from schemas import (
    HoneyPotRequest,
    HoneyPotResponse,
    EngagementMetrics,
    ExtractedIntelligence,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_api_key(x_api_key: Optional[str]) -> None:
    if not x_api_key or x_api_key != HONEYPOT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


@app.get("/")
def health_check() -> dict:
    return {"status": "active"}


@app.post("/honey-pot", response_model=HoneyPotResponse)
async def honey_pot(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
) -> HoneyPotResponse:
    validate_api_key(x_api_key)

    body = await request.json()
    print(f"DEBUG_PAYLOAD: {body}")
    history = body.get("conversationHistory")
    history_count = len(history) if isinstance(history, list) else 0

    response = HoneyPotResponse(
        status="success",
        scamDetected=True,
        engagementMetrics=EngagementMetrics(
            engagementDurationSeconds=0,
            totalMessagesExchanged=history_count + 1,
        ),
        extractedIntelligence=ExtractedIntelligence(
            bankAccounts=[],
            upiIds=[],
            phishingLinks=[],
            phoneNumbers=[],
            suspiciousKeywords=[],
        ),
        agentNotes="Dummy Success",
        reply="Hello, I am confused. What do you mean?",
    )

    return response
