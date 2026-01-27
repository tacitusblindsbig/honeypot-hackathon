from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from brain import HoneypotBrain
import os

app = FastAPI()

# Enable CORS so the tester can reach us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Brain
brain = HoneypotBrain()

@app.get("/")
def health_check():
    return {"status": "active", "service": "HoneyPot-Agent"}

@app.post("/honey-pot")
async def handle_honeypot(request: Request, background_tasks: BackgroundTasks):
    """
    Main Endpoint.
    1. Accepts Request and BackgroundTasks.
    2. Validates API Key.
    3. Passes data + background_tasks to Brain.
    """
    # 1. Parse JSON safely
    try:
        body = await request.json()
        print(f"INCOMING: {body}")
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 2. Security Check
    api_key = request.headers.get("x-api-key")
    server_key = os.getenv("HONEYPOT_API_KEY", "12345")
    
    if api_key != server_key:
        print(f"AUTH FAILED. Expected: {server_key}, Got: {api_key}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 3. Process with Brain (PASSING background_tasks NOW)
    response = await brain.process_incoming_message(body, background_tasks)
    
    # 4. Return as Dict
    return response.model_dump()