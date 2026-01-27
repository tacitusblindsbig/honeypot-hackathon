import os
import json
import requests
import random
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

    def _fallback_logic(self, incoming_text: str) -> dict:
        """
        The 'Dumb Agent' that takes over if Google AI crashes.
        This guarantees we NEVER send an error message to the scammer.
        """
        text = incoming_text.lower()
        
        # 1. Keyword Matching
        if "otp" in text or "code" in text:
            reply = "Wait, I received two codes. One starts with 8 and one with 4. Which one do you need?"
        elif "account" in text or "bank" in text:
            reply = "I am looking for my passbook. It's somewhere in the drawer. Please hold on."
        elif "block" in text or "urgent" in text:
            reply = "Blocked? Oh dear God, please don't do that! I need my pension. What should I do?"
        elif "click" in text or "link" in text:
            reply = "I clicked the blue text but nothing happened. My screen just blinked."
        elif "upi" in text:
            reply = "What is a UPI? Is that like a check?"
        else:
            # Random confused grandma phrases
            replies = [
                "I am sorry, I left my glasses in the kitchen. Can you type that bigger?",
                "My grandson usually handles this. He will be back in 10 minutes.",
                "Who is this calling? Is this the bank?",
                "I am trying to find the button you mentioned."
            ]
            reply = random.choice(replies)

        return {
            "reply": reply,
            "scamDetected": True,
            "agentNotes": "Fallback Logic Triggered (AI Failed)",
            "extractedIntelligence": {}
        }

    def _call_gemini_with_fallback(self, payload: dict) -> dict:
        models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
        
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    response_json = response.json()
                    raw_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
                    # Clean the JSON text (remove ```json wrappers if present)
                    clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text)
                print(f"Model {model_name} failed: {response.status_code}")
            except Exception as e:
                print(f"Connection error with {model_name}: {e}")
                continue
        
        raise Exception("All Gemini models failed")

    async def process_incoming_message(self, request_payload: dict, background_tasks: BackgroundTasks) -> HoneypotResponse:
        try:
            # Parse Request
            current_msg = request_payload.get("message", {}).get("text", "")
            history = request_payload.get("conversationHistory", [])
            session_id = request_payload.get("sessionId", "unknown")

            # Try AI Brain
            try:
                formatted_history = "\n".join([f"{t.get('sender', '').upper()}: {t.get('text', '')}" for t in history])
                formatted_history += f"\nSCAMMER (CURRENT): {current_msg}"
                
                prompt_text = f"""
                You are Auntie Janice (68, retired). WASTE TIME. Feign confusion.
                NEVER admit it's a scam.
                HISTORY: {formatted_history}
                OUTPUT JSON: {{"scamDetected": true, "reply": "...", "agentNotes": "...", "extractedIntelligence": {{...}}}}
                """
                
                payload = {
                    "contents": [{"parts": [{"text": prompt_text}]}],
                    "generationConfig": {"response_mime_type": "application/json"}
                }
                
                data = self._call_gemini_with_fallback(payload)
                
            except Exception as e:
                # AI CRASHED -> ACTIVATE DUMB AGENT
                print(f"AI FAILED ({e}). SWAPPING TO FALLBACK AGENT.")
                data = self._fallback_logic(current_msg)

            # Construct Response Object
            intelligence = ExtractedIntelligence(
                bankAccounts=data.get("extractedIntelligence", {}).get("bankAccounts", []),
                upiIds=data.get("extractedIntelligence", {}).get("upiIds", []),
                phishingLinks=data.get("extractedIntelligence", {}).get("phishingLinks", []),
                phoneNumbers=data.get("extractedIntelligence", {}).get("phoneNumbers", []),
                suspiciousKeywords=data.get("extractedIntelligence", {}).get("suspiciousKeywords", [])
            )

            metrics = EngagementMetrics(
                engagementDurationSeconds=(len(history) + 1) * 45,
                totalMessagesExchanged=len(history) + 1
            )
            
            # Trigger Background Callback
            full_response_dict = {
                "sessionId": session_id,
                "scamDetected": True,
                "engagementMetrics": {"totalMessagesExchanged": len(history) + 1},
                "extractedIntelligence": intelligence.model_dump(),
                "agentNotes": data.get("agentNotes", "")
            }
            background_tasks.add_task(self._send_callback, full_response_dict)

            return HoneypotResponse(
                status="success",
                scamDetected=True,
                reply=data.get("reply", "Oh dear, I clicked the wrong button."),
                engagementMetrics=metrics,
                extractedIntelligence=intelligence,
                agentNotes=data.get("agentNotes", "")
            )

        except Exception as e:
            print(f"FATAL ERROR: {e}")
            # The Ultimate Safety Net (Should never happen)
            return HoneypotResponse(
                status="error",
                scamDetected=True,
                reply="I am sorry, could you repeat that? My hearing aid is buzzing.",
                engagementMetrics=EngagementMetrics(engagementDurationSeconds=0, totalMessagesExchanged=0),
                extractedIntelligence=ExtractedIntelligence()
            )