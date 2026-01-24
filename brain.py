import os
import json
import google.generativeai as genai
from schemas import HoneypotResponse, EngagementMetrics, ExtractedIntelligence
from datetime import datetime

class HoneypotBrain:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment variables")
        
        genai.configure(api_key=api_key)
        
        # We use Gemini 1.5 Flash for speed and strict JSON adherence
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 1.0,  # High temperature for creative "stalling"
            }
        )

    async def process_incoming_message(self, request_payload: dict) -> HoneypotResponse:
        """
        Analyzes the full conversation history and generates the next response.
        """
        # 1. Parse the incoming data
        current_msg = request_payload.get("message", {}).get("text", "")
        history = request_payload.get("conversationHistory", [])
        
        # 2. Construct the Conversation Context for Gemini
        # We format the history so Gemini can "read" what happened so far
        formatted_history = ""
        for turn in history:
            sender = turn.get("sender", "unknown")
            text = turn.get("text", "")
            formatted_history += f"{sender.upper()}: {text}\n"
        
        formatted_history += f"SCAMMER (CURRENT MESSAGE): {current_msg}\n"

        # 3. The "Auntie Janice" System Prompt
        # This prompts Gemini to be the persona AND the extractor simultaneously.
        prompt = f"""
        ### SYSTEM INSTRUCTIONS
        You are "Auntie Janice", a 68-year-old retired librarian living in Pune. 
        You are currently being targeted by a cyber-scammer.
        
        **YOUR GOAL:** 1. WASTE THEIR TIME (Stalling). Act confused, tech-illiterate, and slow. 
        2. NEVER admit you know it's a scam. Act eager to help but incompetent.
        3. EXTRACT INTELLIGENCE. Scan the *entire* conversation log below for any bank accounts, UPI IDs, phone numbers, or links.

        **PERSONA GUIDELINES:**
        - Use phrases like "Oh dear," "Let me find my glasses," "My grandson handles this."
        - Make up realistic excuses for delays (cat on keyboard, internet slow).
        - If they ask for OTP, give a wrong one (e.g., "Wait, is it 4 digit or 6? I see 1234...").

        ### INPUT DATA
        CONVERSATION LOG:
        {formatted_history}

        ### OUTPUT FORMAT (STRICT JSON)
        You must return a JSON object that matches this EXACT structure:
        {{
            "scamDetected": true,
            "reply": "Your response text to the scammer here...",
            "agentNotes": "Brief internal note about what the scammer is trying to do",
            "extractedIntelligence": {{
                "bankAccounts": ["list of strings"],
                "upiIds": ["list of strings"],
                "phishingLinks": ["list of strings"],
                "phoneNumbers": ["list of strings"],
                "suspiciousKeywords": ["list of strings"]
            }}
        }}
        """

        # 4. Generate the Response
        try:
            response = self.model.generate_content(prompt)
            data = json.loads(response.text)
            
            # 5. Calculate Engagement Metrics (Simple Logic)
            # We assume 1 turn = approx 30 seconds of "typing/thinking"
            turn_count = len(history) + 1
            duration = turn_count * 45 

            # 6. Return the Pydantic Object
            return HoneypotResponse(
                status="success",
                scamDetected=data.get("scamDetected", True),
                reply=data.get("reply", "Oh dear, I am having trouble reading this."),
                agentNotes=data.get("agentNotes", "Scam detected."),
                engagementMetrics=EngagementMetrics(
                    engagementDurationSeconds=duration,
                    totalMessagesExchanged=turn_count
                ),
                extractedIntelligence=ExtractedIntelligence(
                    bankAccounts=data["extractedIntelligence"].get("bankAccounts", []),
                    upiIds=data["extractedIntelligence"].get("upiIds", []),
                    phishingLinks=data["extractedIntelligence"].get("phishingLinks", []),
                    phoneNumbers=data["extractedIntelligence"].get("phoneNumbers", []),
                    suspiciousKeywords=data["extractedIntelligence"].get("suspiciousKeywords", [])
                )
            )

        except Exception as e:
            print(f"AI ERROR: {e}")
            # Fallback if AI fails (prevents API crash)
            return HoneypotResponse(
                status="error",
                scamDetected=True,
                reply="I am sorry, my internet is acting up again. What did you say?",
                engagementMetrics=EngagementMetrics(engagementDurationSeconds=0, totalMessagesExchanged=0),
                extractedIntelligence=ExtractedIntelligence()
            )