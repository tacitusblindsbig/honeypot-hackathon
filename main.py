import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from brain import HoneypotBrain


app = FastAPI()
brain = HoneypotBrain()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check() -> dict:
    return {"status": "active"}


@app.post("/honey-pot")
async def handle_honeypot(request: Request) -> dict:
    try:
        body = await request.json()
        print(f"INCOMING: {body}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    api_key = request.headers.get("x-api-key")
    if api_key != os.getenv("HONEYPOT_API_KEY", "12345"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    response = await brain.process_incoming_message(body)
    return response
