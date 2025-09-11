import os
import json
import requests
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Environment variables for Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Placeholder for your AI service URLs
STT_API_URL = "https://your-stt-provider.com/api"
TTS_API_URL = "https://your-tts-provider.com/api"
LLM_API_URL = "https://your-llm-provider.com/api"

# Initialize Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Mock Customer and Technician Database
# In a real-world app, this would be a database query (e.g., Firestore)
CUSTOMER_DB = {
    "+15551234567": {
        "name": "Alice Johnson",
        "last_service": "August 2, 2024",
        "known_issues": "HVAC unit maintenance, furnace filter replacement needed.",
        "customer_type": "Gold"
    },
    "+15559876543": {
        "name": "Bob Williams",
        "last_service": "January 15, 2025",
        "known_issues": "Washing machine repair, noisy motor.",
        "customer_type": "Standard"
    }
}

# -----------------
# API Endpoints
# -----------------

@app.route('/call', methods=['POST'])
def initiate_call():
    """
    Handles the call initiation request from the frontend dashboard.
    """
    to_number = request.form.get('to_number')
    technician_id = request.form.get('technician_id')

    if not to_number or not technician_id:
        return jsonify({"error": "Missing phone number or technician ID"}), 400

    try:
        call = twilio_client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml=f'<Response><Connect><Stream url="wss://your-ngrok-url/twilio_stream"/></Connect></Response>'
        )
        print(f"Call initiated to {to_number} with SID: {call.sid}")
        return jsonify({"status": "Call initiated", "call_sid": call.sid}), 200
    except Exception as e:
        print(f"Twilio call failed: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------
# Twilio Voice Webhook
# -----------------

@app.route('/twilio_voice_webhook', methods=['POST'])
def twilio_voice_webhook():
    """
    This endpoint is called by Twilio when a call is initiated.
    It returns TwiML to start a real-time stream.
    """
    response = VoiceResponse()
    response.say("Connecting you to our AI agent. Please wait.")
    
    connect = Connect()
    connect.stream(url=f'wss://{request.host}/twilio_stream')
    response.append(connect)

    return str(response)

# -----------------
# Real-time WebSocket Communication
# -----------------

@socketio.on('connect')
def handle_frontend_connect():
    """
    Handles a new WebSocket connection from the frontend.
    """
    print("Frontend connected via WebSocket.")

@socketio.on('disconnect')
def handle_frontend_disconnect():
    """
    Handles a WebSocket disconnection from the frontend.
    """
    print("Frontend disconnected.")

@socketio.on('hangup')
def handle_hangup(data):
    """
    Receives a hangup command from the frontend.
    """
    call_sid = data.get('call_sid')
    if call_sid:
        try:
            twilio_client.calls(call_sid).update(status='completed')
            print(f"Hanging up call with SID: {call_sid}")
        except Exception as e:
            print(f"Failed to hang up call: {e}")
    else:
        print("Hangup request received without a call SID.")

# -----------------
# AI Processing Logic (Simulated)
# -----------------

def process_call_stream(audio_data):
    """
    This is a simulated pipeline for real-time AI processing.
    In a real app, this would handle STT, LLM, and TTS.
    """
    # 1. Send audio to STT service
    # stt_response = requests.post(STT_API_URL, data=audio_data)
    # transcript = stt_response.json().get('text')

    # Simulate STT response for demonstration
    transcript = "Hello, my name is Alice, and I have a problem with my HVAC unit."
    print(f"Received transcript: {transcript}")

    # 2. Emit transcript to frontend
    emit('transcript', {'speaker': 'user', 'text': transcript, 'sentiment': 'negative'}, broadcast=True)

    # 3. Send transcript to LLM for a response
    # llm_response = requests.post(LLM_API_URL, json={'prompt': transcript})
    # llm_text = llm_response.json().get('text')
    
    # Simulate LLM response
    llm_text = "Hello Alice, I can help with that. What seems to be the issue?"

    # 4. Emit AI response to frontend
    emit('transcript', {'speaker': 'ai', 'text': llm_text, 'sentiment': 'positive'}, broadcast=True)

    # 5. Send AI text to TTS and stream audio back to Twilio
    # tts_audio = requests.post(TTS_API_URL, json={'text': llm_text})
    # Return TTS audio to the Twilio stream

# -----------------
# Main Application
# -----------------

if __name__ == '__main__':
    # Ensure all required environment variables are set
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("ERROR: Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables.")
    else:
        socketio.run(app, port=5000, debug=True)
