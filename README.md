# Openclaw-ElementX-Bridge (Matrix/Element Messenger to AI Agent)

## 🌟 Overview

This repository contains the **TurboBridge**, a Python bot that acts as a bridge connecting conversational chat on **Matrix/Element** directly to the **Openclaw AI Agent**.

The bot monitors Matrix rooms for user messages, images, and audio files. It processes this content (transcribing audio, downloading media) and sends it to Openclaw for advanced AI processing, returning the intelligent response back into the original Matrix room chat seamlessly.

### 🤖 Key Functionality
*   **Real-time Monitoring:** Monitors specified Matrix rooms asynchronously via sync endpoints.
*   **Multimodal Input Handling:** Accepts and processes text (`m.text`), images (`m.image`), and voice/audio messages (`m.audio`, `m.voice`).
*   **Media Processing:** Downloads media using the Matrix v1 API, cleans multipart data, and saves files temporarily.
*   **Audio Transcription:** Uses **Faster-Whisper** to transcribe audio files into readable text (base model, CPU by default).
*   **AI Integration:** Communicates with the external Openclaw CLI via subprocess, extracting structured responses for use in chat.

## 🚀 Architecture Flow

The process follows a sequential path: User Input → Internal Processing → External AI Call → Output Response.

1.  **User Message (Input):** The user sends content (text, media) to the Matrix room via the Element client.
2.  **TurboBridge (Processing Core):** `matrix_bridge.py` intercepts this event using matrix-nio and determines the message type.
3.  **Media Download & Processing:** If media is detected, the bridge downloads it, extracts binary data, performs necessary pre-processing (e.g., audio transcription), and prepares all context.
4.  **Openclaw AI Agent CLI (Intelligence):** The processed text/context is passed to Openclaw via a subprocess call for AI analysis.
5.  **AI Response JSON:** Openclaw returns the structured result, which the bridge parses.
6.  **Send Response to Matrix Room (Output):** The clean, textual response is then posted back into the original Matrix room, completing the conversation loop.

## 🔧 Websocket Test Client

Test Openclaw Gateway WebSocket connection:

```bash
python3 openclaw_ws_client.py --token API-KEY --chat "Sag kurz hallo"
```

Features:
- Connect challenge / handshake
- Request/response RPCs (health, models.list, sessions.list, chat.send)
- Event listening with auto-reconnect