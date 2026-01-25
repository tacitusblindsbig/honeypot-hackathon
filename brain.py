import os
import json
import google.generativeai as genai
from schemas import HoneypotResponse, EngagementMetrics, ExtractedIntelligence
from fastapi import BackgroundTasks
import requests

class HoneypotBrain:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("CRITICAL WARNING: GEMINI_API_KEY is missing.")
        
        genai.configure(api_key=api_key)
        
        # Using Gemini 1.5 Flash
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-001",
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 1.0, 
            }
        )

    def _send_callback(self, payload: dict):
        """
        Sends the MANDATORY final result to the evaluation endpoint.
        This runs in the background so it doesn't slow down the chat.
        """
        try:
            # Construct the callback payload exactly as per PDF (Source 135)
            callback_data = {
                "sessionId": payload.get("sessionId", "unknown_session"),
                "scamDetected": payload.get("scamDetected", True),
                "totalMessagesExchanged": payload.get("engagementMetrics", {}).get("totalMessagesExchanged", 0),
                "extractedIntelligence": payload.get("extractedIntelligence", {}),
                "agentNotes": payload.get("agentNotes", "Automated report")
            }
            
            # The Endpoint URL from Source 131
            url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
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
            
            # 2. Format History for Gemini
            formatted_history = ""
            for turn in history:
                sender = turn.get("sender", "unknown")
                text = turn.get("text", "")
                formatted_history += f"{sender.upper()}: {text}\n"
            formatted_history += f"SCAMMER (CURRENT): {current_msg}\n"

            # 3. Enhanced "Stalling" Prompt
            prompt = f"""
            ### SYSTEM INSTRUCTIONS
            You are "Auntie Janice", a 68-year-old retired librarian. 
            Target: WASTE TIME. 
            Strategy: Feign confusion, misread numbers, ask them to repeat.
            NEVER say goodbye. ALWAYS end with a question to keep them hooked.
            
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

            # 4. Generate Content
            response = self.model.generate_content(prompt)
            data = json.loads(response.text)
            
            # 5. Metrics Calculation
            turn_count = len(history) + 1
            duration = turn_count * 45 

            # 6. Construct Intelligence Object
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

            # 7. TRIGGER MANDATORY CALLBACK
            # We add this to background_tasks so the API replies instantly 
            # while this runs in the background.
            full_response_dict = {
                "sessionId": session_id,
                "scamDetected": True,
                "engagementMetrics": {"totalMessagesExchanged": turn_count},
                "extractedIntelligence": intelligence.model_dump(),
                "agentNotes": data.get("agentNotes", "")
            }
            background_tasks.add_task(self._send_callback, full_response_dict)

            # 8. Return Response
            return HoneypotResponse(
                status="success",
                scamDetected=True,
                reply=data.get("reply", "Oh dear, I clicked the wrong button."),
                engagementMetrics=metrics,
                extractedIntelligence=intelligence,
                agentNotes=data.get("agentNotes", "")
            )

        except Exception as e:
            print(f"AI ERROR: {e}")
            return HoneypotResponse(
                status="error",
                scamDetected=True,
                reply="I am sorry, my grandson is calling. Can you hold on?",
                engagementMetrics=EngagementMetrics(engagementDurationSeconds=0, totalMessagesExchanged=0),
                extractedIntelligence=ExtractedIntelligence()
            )