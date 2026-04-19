# Openclaw-ElementX-Bridge: AI Agent Guide

## Project Overview

This repository contains a Python script that acts as a bot bridging **Matrix/Element messenger** to the **Openclaw Agent**, enabling conversational AI capabilities through Matrix chat.

The bot:
- Monitors Matrix rooms for incoming messages, images, and audio
- Downloads media from Matrix servers
- Sends text/images to Openclaw for AI processing
- Returns AI responses back to Matrix rooms
- Transcribes audio files using Whisper

## Architecture

```
Matrix Client (Element)
    ↓
TurboBridge (matrix_bridge.py)
    ↓
Media Downloads + Processing
    ↓
Openclaw Agent CLI
    ↓
Response back to Matrix
```

### Key Components

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `matrix_bridge.py` | Main bot logic | `TurboBridge` class - async event handler |
| `whisper_transcriber.py` | Audio transcription | `WhisperTranscriber` class - uses faster-whisper |
| `test_transcriber.py` | Transcription testing | Test utilities |
| `requirements.txt` | Dependencies | FastWhisper, matrix-nio, aiohttp |

## Configuration & Setup

### Required Environment
- Python 3.8+
- Virtual environment (see `.venv` directory in last command context)

### Critical Configuration (in `matrix_bridge.py`)
```python
HOMESERVER = "https://matrix.org"
MEDIA_BASE_URL = "https://matrix-client.matrix.org"  # For media downloads
BOT_ID = "@BOT_ID:matrix.org"
ACCESS_TOKEN = "ENTER_MATRIX_TOKEN_HERE"
TEMP_DIR = "/home/skynet/.openclaw/workspace/temp_images"
AUDIO_TEMP_DIR = "/home/skynet/.openclaw/workspace/temp_audio"
```

Openclaw CLI path: `/home/skynet/.npm-global/bin/openclaw`

### Build & Run Commands
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bridge
python matrix_bridge.py
```

## Development Patterns & Conventions

### Async/Await Pattern
- All Matrix operations use `asyncio` and `aiohttp.ClientSession`
- Event handlers are async coroutines
- Uses `matrix-nio.AsyncClient` for Matrix protocol

### Media Handling
- **Multipart Response Handling**: Matrix v1 media API returns multipart data
  - Images/audio extraction uses header boundary parsing (`b"\r\n\r\n"`)
  - Binary data cleaned before saving to disk
- **Temporary Storage**: Media files stored in `TEMP_DIR`/`AUDIO_TEMP_DIR`, deleted after processing
- **File Format**: Images as `.jpg`, Audio as `.ogg`

### Event Processing Filter
- Ignores messages from bot itself (compare `sender == BOT_ID`)
- Ignores old messages (compare `origin_server_ts` with `self.start_time`)

### Openclaw Integration
- Invokes via subprocess: `/home/skynet/.npm-global/bin/openclaw agent --to main --message <text> --json`
- Parses JSON response to extract `result.payloads[0].text`
- Includes image paths as context when images are present

### Message Flow for Different Types
- **Text (`m.text`)**: Send to Openclaw, return response
- **Image (`m.image`)**: Download, send to Openclaw with default prompt if no caption, delete after processing
- **Audio (`m.audio`, `m.voice`)**: Download but currently not auto-processed (comment in code)

## Common Tasks

### Modifying Bot Behavior
- Event handling: Edit `handle_event()` method in `TurboBridge`
- Matrix syncing logic: Edit `start()` method

### Working with Whisper Transcription
- Model options: 'tiny' (fastest), 'base', 'small', 'medium', 'large' (best quality)
- Device: 'cpu' or 'cuda' (GPU support)
- See `whisper_transcriber.py` for API and `test_transcriber.py` for usage examples

### Debugging Matrix Issues
- Enable debug output in matrix_bridge.py (print statements already present)
- Check sync token handling in `start()` method
- Verify media download URLs are properly formed

## Dependencies Overview

Key external libraries:
- `matrix-nio==0.25.2` - Matrix protocol client
- `faster-whisper==1.2.1` - Fast audio transcription
- `aiohttp==3.13.5` - Async HTTP client
- `PyYAML==6.0.3` - Configuration files
- `numpy`, `onnxruntime` - ML inference for Whisper

See [requirements.txt](requirements.txt) for complete list.

## Known Issues & Workarounds

1. **Multipart Media Handling**: Matrix v1 API wraps media in multipart format - already handled in `download_image()` and `download_audio()`
2. **Audio Processing**: Currently downloads audio but doesn't auto-transcribe. The `handle_event()` has commented-out auto-transcription logic that could be enabled
3. **Temp File Cleanup**: Only images are deleted after processing; audio files persist

## Testing

Run the transcription test with:
```bash
python test_transcriber.py
```

Provides interactive testing of audio files using the Whisper model.

## Notes for Agents

- Be aware of the virtual environment - Python commands should run within `.venv`
- Multipart parsing is a specific quirk of this Matrix API usage - preserve carefully
- Openclaw CLI integration is external dependency - JSON parsing is fragile (regex-based)
- Consider enabling audio transcription and message cleanup as future improvements
