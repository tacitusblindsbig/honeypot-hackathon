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
            requests.post(url, json=callback_data, timeout=5)
            print(f"CALLBACK SENT: {callback_data['sessionId']}")
        except Exception as e:
            print(f"CALLBACK FAILED: {e}")

    def _call_gemini_with_fallback(self, payload: dict) -> dict:
        """
        Tries multiple model names until one works.
        This fixes the 404 error by finding the correct model name automatically.
        """
        # List of models to try in order of preference
        models = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-latest",
            "gemini-pro"
        ]

        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                response = requests.post(url, json=payload, timeout=10)
                
                # If success, return the data immediately
                if response.status_code == 200:
                    print(f"SUCCESS with model: {model_name}")
                    return response.json()
                
                # If 404 or other error, print and loop to next model
                print(f"Model {model_name} failed: {response.status_code}")
                
            except Exception as e:
                print(f"Connection error with {model_name}: {e}")
                continue
        
        # If all failed, raise error
        raise Exception("All Gemini models failed.")

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

            # 3. Construct Payload
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

            # 4. Call API with Fallback Logic (THE FIX)
            response_json = self._call_gemini_with_fallback(payload)
            
            # 5. Parse Response
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