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
async def handle_honeypot(request: Request):
    # 1. Get Raw JSON (Bypass strict validation for safety, parse manually)
    try:
        body = await request.json()
        print(f"INCOMING: {body}") # Keep logging for debug
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 2. Check API Key (Security)
    api_key = request.headers.get("x-api-key")
    if api_key != os.getenv("HONEYPOT_API_KEY", "12345"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 3. Let the Brain process it
    response = await brain.process_incoming_message(body)
    
    # 4. Return as Dict (The Fix: Convert Pydantic object to Dictionary)
    return response.model_dump()
