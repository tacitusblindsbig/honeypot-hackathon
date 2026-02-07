# 🛡️ Agentic Honeypot: AI Scam Interceptor

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.68%2B-green)
![AI Model](https://img.shields.io/badge/AI-Llama3%20%2F%20GPT4o-purple)
![License](https://img.shields.io/badge/License-MIT-orange)

## 📖 Overview

**Agentic Honeypot** is an intelligent, automated counter-scam system designed to intercept, engage, and extract intelligence from cybercriminals. 

Deployed as a high-availability REST API, the system employs a **State-Aware AI Persona ("Auntie Janice")** to waste scammers' time while silently harvesting critical data (UPI IDs, bank accounts, phishing links) and reporting it to a central authority.

## 🚀 Key Features

* **🎭 Adaptive AI Persona**: Engages scammers using a confused, elderly persona ("Auntie Janice") to prolong engagement without raising suspicion.
* **🧠 Provider-Agnostic Brain**: Built with a flexible routing layer (FastRouter) capable of switching between **Llama-3-70B**, **Claude 3.5 Sonnet**, and **GPT-4o** for maximum resilience.
* **🔄 Anti-Loop Logic**: Implements a "Smart Fallback" agent that detects repetitive conversation loops and dynamically shifts topics to maintain realism.
* **🕵️ Real-Time Intelligence**: Automatically parses conversation history to extract structured threat data (Phone Numbers, UPIs) in JSON format.
* **📡 Mandatory Reporting**: Features an asynchronous background task that reports detected threats to the Cybercrime Evaluation Endpoint immediately.
* **💓 High Availability**: Hosted on **Render Cloud** with a custom "Heartbeat" monitor (UptimeRobot) to prevent cold-starts and ensure sub-second latency.

## 🛠️ Tech Stack

* **Core Framework**: FastAPI (Python)
* **AI Inference**: FastRouter (routing to Meta Llama 3 / OpenAI GPT-4o)
* **Deployment**: Render (Cloud Hosting)
* **Resilience**: UptimeRobot (Keyword Monitoring)
* **Validation**: Pydantic

## ⚙️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/your-username/honeypot-hackathon.git](https://github.com/your-username/honeypot-hackathon.git)
    cd honeypot-hackathon
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**
    Create a `.env` file in the root directory:
    ```env
    HONEYPOT_API_KEY=your_secure_password
    LLM_API_KEY=your_fastrouter_key
    LLM_BASE_URL=[https://go.fastrouter.ai/api/v1](https://go.fastrouter.ai/api/v1)
    LLM_MODEL=meta-llama/llama-3-70b-instruct
    ```

4.  **Run Locally**
    ```bash
    uvicorn main:app --reload
    ```

## 🔌 API Usage

The system exposes a single POST endpoint.

**Endpoint:** `POST /honey-pot`

**Example Request:**
```bash
curl -X POST "http://localhost:8000/honey-pot" \
     -H "Content-Type: application/json" \
     -H "x-api-key: your_secure_password" \
     -d '{
           "sessionId": "test-session-101",
           "message": {
             "text": "URGENT: Your account is blocked. Send OTP immediately.",
             "sender": "scammer"
           },
           "conversationHistory": []
         }'


graph TD
    A[Scammer Input] -->|POST Request| B(FastAPI Endpoint)
    B --> C{Authentication Check}
    C -->|Valid| D[AI Brain Engine]
    C -->|Invalid| E[401 Unauthorized]
    
    D -->|Step 1| F[Context Analysis]
    F -->|Step 2| G{AI Availability Check}
    
    G -->|Available| H[Call FastRouter/Llama-3]
    G -->|Unavailable| I[Smart Fallback Agent]
    
    H --> J[Response Generation]
    I --> J
    
    J --> K[Background Task: Report to Authority]
    J --> L[Return JSON to Scammer]

