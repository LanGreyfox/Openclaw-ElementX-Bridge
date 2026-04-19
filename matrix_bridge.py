import asyncio
import json
import re
import time
import aiohttp
import os
from nio import AsyncClient
from whisper_transcriber import WhisperTranscriber

# --- Configuration ---
HOMESERVER = "https://matrix.org"
# Specific URL for media download (per documentation)
MEDIA_BASE_URL = "https://matrix-client.matrix.org"
BOT_ID = "@BOT_ID:matrix.org"
ACCESS_TOKEN = "ENTER_MATRIX_TOKEN_HERE"

# Directories for temporary images and audio
TEMP_DIR = "/home/skynet/.openclaw/workspace/temp_images"
AUDIO_TEMP_DIR = "/home/skynet/.openclaw/workspace/temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
# ---------------------

class TurboBridge:
    def __init__(self):
        self.client = AsyncClient(HOMESERVER, BOT_ID)
        self.client.access_token = ACCESS_TOKEN
        self.sync_token = None
        self.start_time = time.time() * 1000
        self.transcriber = WhisperTranscriber(model_size="base", device="cpu")

    async def download_image(self, session, mxc_url):
        """Downloads the image via the v1 path and cleans multipart data."""
        try:
            mxc_parts = mxc_url.replace("mxc://", "").split("/")
            server_name, media_id = mxc_parts[0], mxc_parts[1]
            
            # Path from v1 documentation
            url = f"{MEDIA_BASE_URL}/_matrix/client/v1/media/download/{server_name}/{media_id}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            
            print(f"DEBUG: Attempting v1-Download of {url}")

            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    raw_data = await resp.read()
                    
                    # Multipart handling: Extract actual image data
                    # Images in multipart start after the header block (\r\n\r\n)
                    if b"\r\n\r\n" in raw_data:
                        print("📦 Multipart found, extracting binary data...")
                        parts = raw_data.split(b"\r\n\r\n")
                        # We take the part after headers and trim footer
                        image_data = parts[1].split(b"\r\n--")[0]
                    else:
                        image_data = raw_data

                    file_path = os.path.join(TEMP_DIR, f"img_{int(time.time())}.jpg")
                    with open(file_path, "wb") as f:
                        f.write(image_data)
                    
                    print(f"✅ Image saved locally: {file_path}")
                    return file_path
                else:
                    print(f"❌ Download failed: Status {resp.status}")
                    return None
        except Exception as e:
            print(f"⚠️ Error during download: {e}")
            return None

    async def download_audio(self, session, mxc_url):
        """Downloads the audio file and saves it."""
        try:
            # Audio is also loaded via v1-Media
            mxc_parts = mxc_url.replace("mxc://", "").split("/")
            server_name, media_id = mxc_parts[0], mxc_parts[1]
            
            url = f"{MEDIA_BASE_URL}/_matrix/client/v1/media/download/{server_name}/{media_id}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            
            print(f"🎵 Audio download from {url}")

            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    raw_data = await resp.read()
                    
                    # Multipart-Handling für Audio
                    if b"\r\n\r\n" in raw_data:
                        print("📦 Multipart detected, extracting binary data...")
                        parts = raw_data.split(b"\r\n\r\n")
                        audio_data = parts[1].split(b"\r\n--")[0]
                    else:
                        audio_data = raw_data

                    file_path = os.path.join(AUDIO_TEMP_DIR, f"audio_{int(time.time())}.ogg")
                    with open(file_path, "wb") as f:
                        f.write(audio_data)
                    
                    print(f"✅ Audio saved locally: {file_path}")
                    return file_path
                else:
                    print(f"❌ Audio download failed: Status {resp.status}")
                    return None
        except Exception as e:
            print(f"⚠️ Error during audio download: {e}")
            return None

    async def send_to_openclaw(self, text, image_path=None):
        """Invokes OpenClaw. If an image is present, the path is given."""
        message_content = text
        if image_path:
            message_content = f"I have a local image saved here: {image_path}. With the following text {text}"

        try:
            process = await asyncio.create_subprocess_exec(
                "/home/skynet/.npm-global/bin/openclaw", "agent", "--to", "main", "--message", message_content, "--json",
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode().strip()
            
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                payloads = data.get("result", {}).get("payloads", [])
                if payloads:
                    return payloads[0].get("text", "AI has not provided any text.")
            return "Error: Could not process the AI's response."
        except Exception as e:
            return f"Error calling OpenClaw: {e}"

    async def handle_event(self, session, room_id, event):
        """Processes text, images and audio."""
        content = event.get("content", {})
        msgtype = content.get("msgtype")
        sender = event.get("sender")
        ts = event.get("origin_server_ts", 0)

        # Safety check
        if sender == BOT_ID or ts <= self.start_time:
            return

        image_path = None
        body = content.get("body", "")

        # Image logic
        if msgtype == "m.image":
            print(f"🖼️ Image received from {sender}")
            mxc_url = content.get("url")
            image_path = await self.download_image(session, mxc_url)
            # Default prompt if no text with image
            if not body or body.startswith("mxc://"):
                body = "Beschreibe dieses Bild."

        # Audio logic
        if msgtype in ["m.audio", "m.voice"]:
            print(f"🎵 Audio received from {sender}")
            mxc_url = content.get("url")
            media_path = await self.download_audio(session, mxc_url)
            if media_path:
                try:
                    body = self.transcriber.transcribe_and_get_text(media_path)
                    print(f"✅ Audio transcribed: {body[:50]}...")
                except Exception as e:
                    print(f"⚠️ Transcription failed: {e}")
                    body = "Audio konnte nicht transkribiert werden."

        # Send message to OpenClaw (if text, image or audio present)
        if msgtype in ["m.text", "m.image", "m.audio", "m.voice"]:
            print(f"🗨️ Processing: {body[:50]}...")
            answer = await self.send_to_openclaw(body, image_path)
            
            await self.client.room_send(
                room_id, "m.room.message", 
                {"msgtype": "m.text", "body": str(answer)}
            )
            print(f"✅ Response sent.")
            
            # Delete media after processing
            if image_path and os.path.exists(image_path):
                os.remove(image_path)

            # Delete audio after processing
            if media_path and os.path.exists(media_path):
                os.remove(media_path)

    async def start(self):
        print("--- Matrix-OpenClaw Turbo-Bridge (V1-Media-Fix) started ---")
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            print("🔄 Priming...")
            initial_url = f"{HOMESERVER}/_matrix/client/r0/sync?timeout=0"
            async with session.get(initial_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.sync_token = data.get("next_batch")
                    print("🚀 Ready!")
                else:
                    print(f"❌ Error during initial sync: {resp.status}")
                    return

            while True:
                try:
                    url = f"{HOMESERVER}/_matrix/client/r0/sync?timeout=30000"
                    if self.sync_token:
                        url += f"&since={self.sync_token}"
                    
                    async with session.get(url, headers=headers, timeout=45) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.sync_token = data.get("next_batch")
                            rooms = data.get("rooms", {}).get("join", {})
                            for room_id, room_data in rooms.items():
                                events = room_data.get("timeline", {}).get("events", [])
                                for event in events:
                                    if event.get("type") == "m.room.message":
                                        # We use handle_event for text & media
                                        asyncio.create_task(self.handle_event(session, room_id, event))
                        
                        elif response.status == 401:
                            print("❌ Invalid token!")
                            await asyncio.sleep(60)
                        else:
                            await asyncio.sleep(10)

                except Exception as e:
                    print(f"🌐 Network error: {e}. Reconnecting in 5s...")
                    await asyncio.sleep(5)

if __name__ == "__main__":
    bridge = TurboBridge()
    try:
        asyncio.run(bridge.start())
    except KeyboardInterrupt:
        print("\n👋 Bridge stopped.")