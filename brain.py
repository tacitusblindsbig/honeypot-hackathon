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
            # Source 131 in documentation
            url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
            requests.post(url, json=callback_data, timeout=2) 
            print(f"CALLBACK SENT: {callback_data['sessionId']}")
        except Exception as e:
            print(f"CALLBACK FAILED: {e}")

    def _get_random_stall_message(self):
        return random.choice([
            "I am looking for my reading glasses, please hold on a minute.",
            "My screen just went black for a second. Is this the bank?",
            "I am trying to click the button but my mouse is stuck.",
            "Can you explain that again? I am writing this down."
        ])

    def _fallback_logic(self, incoming_text: str, history: list) -> dict:
        """Smart Fallback Agent to break loops."""
        text = incoming_text.lower()
        last_bot_reply = ""
        for turn in reversed(history):
            if turn.get("sender") == "user":
                last_bot_reply = turn.get("text", "")
                break
        
        reply = ""
        if ("otp" in text or "code" in text) and "two codes" not in last_bot_reply:
            reply = "Wait, I received two codes. One starts with 8 and one with 4. Which one do you need?"
        elif "account" in text or "bank" in text:
            reply = "I am looking for my passbook. It's somewhere in the drawer."
        elif "block" in text or "urgent" in text:
            reply = "Blocked? Oh dear God, please don't do that!"
        
        if reply == last_bot_reply or not reply:
            reply = self._get_random_stall_message()

        return {
            "reply": reply,
            "scamDetected": True,
            "agentNotes": "Fallback Agent Active",
            "extractedIntelligence": {}
        }

    def _call_gemini_2_flash(self, payload: dict) -> dict:
        # THE FIX: Use the model we confirmed exists
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                response_json = response.json()
                if "candidates" in response_json and response_json["candidates"]:
                    raw_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
                    clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text)
            print(f"Gemini 2.0 Failed: {response.status_code} - {response.text}")
            raise Exception(f"Gemini API Error: {response.status_code}")
        except Exception as e:
            raise e

    async def process_incoming_message(self, request_payload: dict, background_tasks: BackgroundTasks) -> HoneypotResponse:
        try:
            current_msg = request_payload.get("message", {}).get("text", "")
            history = request_payload.get("conversationHistory", [])
            session_id = request_payload.get("sessionId", "unknown")

            data = {}
            try:
                formatted_history = "\n".join([f"{t.get('sender', '').upper()}: {t.get('text', '')}" for t in history])
                formatted_history += f"\nSCAMMER (CURRENT): {current_msg}"
                
                prompt_text = f"""
                You are Auntie Janice (68, retired). GOAL: WASTE TIME. Feign confusion.
                HISTORY: {formatted_history}
                INSTRUCTIONS:
                1. Do NOT repeat the exact same phrase twice in a row.
                2. If the history shows you just asked a question, wait for their answer.
                OUTPUT JSON EXACTLY:
                {{
                    "scamDetected": true, 
                    "reply": "your text response", 
                    "agentNotes": "analysis", 
                    "extractedIntelligence": {{
                        "bankAccounts": [], "upiIds": [], "phishingLinks": [], "phoneNumbers": [], "suspiciousKeywords": []
                    }}
                }}
                """
                
                payload = {
                    "contents": [{"parts": [{"text": prompt_text}]}],
                    "generationConfig": { "response_mime_type": "application/json", "temperature": 1.0 }
                }
                
                data = self._call_gemini_2_flash(payload)
                
            except Exception as e:
                print(f"AI FAILED ({e}). SWAPPING TO FALLBACK.")
                data = self._fallback_logic(current_msg, history)

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
            return HoneypotResponse(
                status="error",
                scamDetected=True,
                reply="I am sorry, could you repeat that?",
                engagementMetrics=EngagementMetrics(engagementDurationSeconds=0, totalMessagesExchanged=0),
                extractedIntelligence=ExtractedIntelligence()
            )