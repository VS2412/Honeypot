## Honeypot – AI-Powered Scam Detection & Intelligence Gathering System
Overview

Honeypot is an AI-driven cybersecurity solution designed to identify, engage, and analyze scam conversations in real time. 

The system acts as a simulated victim, interacts with suspected scammers using an AI-powered persona, collects actionable intelligence such as UPI IDs, phone numbers, and phishing links, and generates structured reports for security analysis.

## Key Features
Real-time scam intent detection

AI-powered conversational engagement using Mistral LLM

Extraction of UPI IDs, phone numbers, and phishing links

Session-based conversation tracking

Automated scam confirmation through scoring mechanisms

## Tech Stack
## Backend
Python

FastAPI

Pydantic

Uvicorn

AI & NLP

Mistral LLM

Ollama

Security & Intelligence Extraction

Regular Expressions (Regex)

Scam Intent Scoring Engine

APIs & Integration

REST APIs

Callback Reporting System

Deployment

Render

## System Architecture

```mermaid
flowchart TD

    User["📱 Incoming Message"]

    API["⚡ FastAPI Backend
    - REST API
    - Session Handling
    - Request Validation"]

    Detection["🛡️ Scam Detection Engine
    - Keyword Analysis
    - Scam Scoring
    - Intent Detection"]

    LLM["🤖 AI Honeypot Agent
    (Mistral via Ollama)
    - Human-like Responses
    - Information Gathering
    - Dynamic Persona"]

    Extractor["🔍 Intelligence Extraction
    - UPI IDs
    - Phone Numbers
    - Phishing URLs
    - Suspicious Keywords"]

    Session["📂 Session Store"]

    Report["📄 Report Generator"]

    Callback["📡 GUVI Callback API"]

    User --> API
    API --> Detection
    Detection --> LLM
    LLM --> Extractor
    Extractor --> Session
    Session --> Report
    Report --> Callback
```

## Workflow
A message is received through the Honeypot API. 

The Scam Detection Engine evaluates the message using predefined scam indicators. 

A scam score is calculated. 

If the score exceeds the threshold, the scam is confirmed. 

The AI-powered Honeypot Persona engages the scammer naturally. 

Intelligence such as UPI IDs, phone numbers, and phishing URLs is extracted. 

The system monitors conversation progress and determines when sufficient intelligence has been collected. 

The conversation is terminated automatically. 

A final intelligence report is generated and sent to the reporting endpoint. 


## API Endpoint
## POST /api/honeypot/message

Receives incoming messages and generates an appropriate response.

## Request Headers
X-API-Key: your_api_key
## Sample Response
{
  "status": "success",
  "reply": "Generated AI response"
}



## Future Enhancements
Machine Learning-based scam classification

Multi-language support

Dashboard for live monitoring

Advanced phishing detection

Fraud pattern analytics

Real-time threat intelligence integration
