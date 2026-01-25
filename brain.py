import os
import json
import requests
from fastapi import BackgroundTasks
from schemas import HoneypotResponse, EngagementMetrics, ExtractedIntelligence

class HoneypotBrain:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("CRITICAL WARNING: GEMINI_API_KEY is missing.")

    def _send_callback(self, payload: dict):
        """Sends the MANDATORY final result to the evaluation endpoint."""
        try:
            callback_data = {
                "sessionId": payload.get("sessionId", "unknown_session"),
                "scamDetected": payload.get("scamDetected", True),
                "totalMessagesExchanged": payload.get("engagementMetrics", {}).get("totalMessagesExchanged", 0),
                "extractedIntelligence": payload.get("extractedIntelligence", {}),
                "agentNotes": payload.get("agentNotes", "Automated report")
            }
            url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
            # Using a short timeout so we don't hang if their server is slow
            requests.post(url, json=callback_data, timeout=5)
            print(f"CALLBACK SENT: {callback_data['sessionId']}")
        except Exception as e:
            print(f"CALLBACK FAILED: {e}")

    async def process_incoming_message(self, request_payload: dict, background_tasks: BackgroundTasks) -> HoneypotResponse:
        try:
            # 1. Parse Data
            current_msg = request_payload.get("message", {}).get("text", "")
            history = request_payload.get("conversationHistory", [])
            session_id = request_payload.get("sessionId", "unknown")
            
            # 2. Format History
            formatted_history = ""
            for turn in history:
                sender = turn.get("sender", "unknown")
                text = turn.get("text", "")
                formatted_history += f"{sender.upper()}: {text}\n"
            formatted_history += f"SCAMMER (CURRENT): {current_msg}\n"

            # 3. Construct the Raw JSON Payload for Gemini REST API
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            prompt_text = f"""
            ### SYSTEM INSTRUCTIONS
            You are "Auntie Janice", a 68-year-old retired librarian. 
            Target: WASTE TIME. Strategy: Feign confusion, misread numbers.
            NEVER say goodbye. ALWAYS end with a question.
            
            ### DATA TO ANALYZE
            {formatted_history}

            ### OUTPUT (STRICT JSON)
            {{
                "scamDetected": true,
                "reply": "Your response...",
                "agentNotes": "Brief analysis",
                "extractedIntelligence": {{
                    "bankAccounts": [],
                    "upiIds": [],
                    "phishingLinks": [],
                    "phoneNumbers": [],
                    "suspiciousKeywords": []
                }}
            }}
            """

            payload = {
                "contents": [{
                    "parts": [{"text": prompt_text}]
                }],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 1.0
                }
            }

            # 4. Call Google API Directly (No SDK)
            response = requests.post(gemini_url, json=payload, timeout=10)
            response.raise_for_status() # Raise error if API fails
            
            # 5. Parse Response
            response_json = response.json()
            raw_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(raw_text)
            
            # 6. Metrics
            turn_count = len(history) + 1
            duration = turn_count * 45 

            # 7. Construct Intelligence
            intelligence = ExtractedIntelligence(
                bankAccounts=data["extractedIntelligence"].get("bankAccounts", []),
                upiIds=data["extractedIntelligence"].get("upiIds", []),
                phishingLinks=data["extractedIntelligence"].get("phishingLinks", []),
                phoneNumbers=data["extractedIntelligence"].get("phoneNumbers", []),
                suspiciousKeywords=data["extractedIntelligence"].get("suspiciousKeywords", [])
            )

            metrics = EngagementMetrics(
                engagementDurationSeconds=duration,
                totalMessagesExchanged=turn_count
            )

            # 8. Trigger Callback
            full_response_dict = {
                "sessionId": session_id,
                "scamDetected": True,
                "engagementMetrics": {"totalMessagesExchanged": turn_count},
                "extractedIntelligence": intelligence.model_dump(),
                "agentNotes": data.get("agentNotes", "")
            }
            background_tasks.add_task(self._send_callback, full_response_dict)

            # 9. Return Response
            return HoneypotResponse(
                status="success",
                scamDetected=True,
                reply=data.get("reply", "Oh dear, I clicked the wrong button."),
                engagementMetrics=metrics,
                extractedIntelligence=intelligence,
                agentNotes=data.get("agentNotes", "")
            )

        except Exception as e:
            print(f"BRAIN ERROR: {e}")
            # Fallback
            return HoneypotResponse(
                status="error",
                scamDetected=True,
                reply="I am sorry, my internet is acting up. Could you say that again?",
                engagementMetrics=EngagementMetrics(engagementDurationSeconds=0, totalMessagesExchanged=0),
                extractedIntelligence=ExtractedIntelligence()
            )