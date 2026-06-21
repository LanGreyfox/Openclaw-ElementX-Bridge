# Matrix-OpenClaw Turbo-Bridge (V1-Media-Fix)
#
# This script connects an Element Matrix bot with the Openclaw AI Agent. 
# It receives messages, images and audios from Matrix rooms, processes them via Openclaw API,
# sends results back as text replies, and deletes temporary media files.
#
# Key functions:
# - V1-media download with multipart handling (b"\r\n\r\n" -> b"--")
# - Audio transcription via WhisperTranscriber (base model, CPU)
# - OpenClaw call via subprocess and JSON parse
# - Automatic media cleanup after processing

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
OPENCLAW_LOG_COMMAND = 'openclaw logs --json | jq -c \'select(.type == "log" and .subsystem == null) | {timestamp: .time, message: .message}\''
LOG_POLL_INTERVAL_SECONDS = 60

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
        self.joined_rooms = set()
        self.seen_logs = set()

    async def _download_media(self, session, mxc_url, temp_dir, extension):
        """Generalized function to download media (images/audio) via v1 path and handles multipart data."""
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
                    
                    # Multipart handling: Extract actual binary data
                    if b"\r\n\r\n" in raw_data:
                        print("📦 Multipart found, extracting binary data...")
                        parts = raw_data.split(b"\r\n\r\n")
                        media_data = parts[1].split(b"\r\n--")[0]
                    else:
                        media_data = raw_data

                    file_path = os.path.join(temp_dir, f"media_{int(time.time())}{extension}")
                    with open(file_path, "wb") as f:
                        f.write(media_data)
                    
                    print(f"✅ Media saved locally: {file_path}")
                    return file_path
                else:
                    print(f"❌ Download failed: Status {resp.status}")
                    return None
        except Exception as e:
            print(f"⚠️ Error during media download: {e}")
            return None

    async def download_image(self, session, mxc_url):
        """Downloads the image via the v1 path and cleans multipart data."""
        # Calls generalized helper function for consistency
        return await self._download_media(session, mxc_url, TEMP_DIR, ".jpg")

    async def download_audio(self, session, mxc_url):
        """Downloads the audio file and saves it."""
        # Calls generalized helper function for consistency
        return await self._download_media(session, mxc_url, AUDIO_TEMP_DIR, ".ogg")

    async def send_to_openclaw(self, text, image_path=None):
        """Invokes OpenClaw. If an image is present, the path is given."""
        message_content = text
        if image_path:
            message_content = f"Ich habe hier ein lokales Bild hinterlegt: {image_path}. Mit folgendem Text {text}"

        try:
            start_time = time.time()
            print(f"⏱️ Starting OpenClaw subprocess at {start_time:.2f}")
            
            process = await asyncio.create_subprocess_exec(
                "/home/skynet/.npm-global/bin/openclaw", "agent", "--to", "main", "--message", message_content, "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            subprocess_start_time = time.time()
            print(f"⏱️ Subprocess created in {subprocess_start_time - start_time:.2f} seconds")
            
            stdout, stderr = await process.communicate()
            communicate_time = time.time()
            print(f"⏱️ Subprocess communicate finished in {communicate_time - subprocess_start_time:.2f} seconds")
            
            output = stdout.decode().strip()

            match = re.search(r'\{.*\}', output, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                payloads = data.get("result", {}).get("payloads", [])
                if payloads:
                    # Collect all texts from payloads
                    all_texts = []
                    for payload in payloads:
                        text_content = payload.get("text", "").strip()
                        if text_content:
                            all_texts.append(text_content)

                    if all_texts:
                        # collect all texts with separator
                        end_time = time.time()
                        print(f"⏱️ Total OpenClaw processing time: {end_time - start_time:.2f} seconds")
                        return "\n\n---\n\n".join(all_texts)

            end_time = time.time()
            print(f"⏱️ Total OpenClaw processing time: {end_time - start_time:.2f} seconds")
            return "Error: Could not process the AI's response."
        except Exception as e:
            return f"Error calling OpenClaw: {e}"

    def update_joined_rooms(self, sync_data):
        rooms = sync_data.get("rooms", {}).get("join", {})
        self.joined_rooms = set(rooms.keys())
        print(f"🔁 Joined rooms updated ({len(self.joined_rooms)}): {sorted(self.joined_rooms)}")

    async def fetch_openclaw_log_entries(self):
        print(f"🔍 Fetching OpenClaw logs with command: {OPENCLAW_LOG_COMMAND}")
        try:
            process = await asyncio.create_subprocess_shell(
                OPENCLAW_LOG_COMMAND,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                message = stderr.decode().strip()
                print(f"⚠️ OpenClaw log command failed ({process.returncode}): {message}")
                return []

            output = stdout.decode().strip()
            if not output:
                print("ℹ️ OpenClaw logs returned no output.")
                return []

            lines = output.splitlines()
            print(f"ℹ️ OpenClaw log fetch returned {len(lines)} line(s).")
            entries = []
            for line in lines:
                print(f"📄 Parsing log line: {line}")
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Failed to parse OpenClaw log line: {line} ({e})")
                    continue

                timestamp = data.get("timestamp")
                message = data.get("message")
                if timestamp is None or message is None:
                    continue

                entries.append({"timestamp": timestamp, "message": message})

            return entries
        except Exception as e:
            print(f"⚠️ Error fetching OpenClaw logs: {e}")
            return []

    async def broadcast_log_entries(self, entries):
        if not self.joined_rooms:
            print("ℹ️ No joined rooms available for log broadcast.")
            return

        body = "\n".join(f"[{entry['timestamp']}] {entry['message']}" for entry in entries)
        for room_id in self.joined_rooms:
            try:
                await self.client.room_send(
                    room_id,
                    "m.room.message",
                    {"msgtype": "m.text", "body": body}
                )
                print(f"✅ Sent OpenClaw log update to {room_id}")
            except Exception as e:
                print(f"⚠️ Failed to send log update to {room_id}: {e}")

    async def openclaw_log_watcher(self):
        print("🚧 OpenClaw log watcher started.")
        while True:
            print("⏱️ Polling OpenClaw logs...")
            entries = await self.fetch_openclaw_log_entries()
            new_entries = []
            for entry in entries:
                fingerprint = f"{entry['timestamp']}|{entry['message']}"
                if fingerprint not in self.seen_logs:
                    self.seen_logs.add(fingerprint)
                    new_entries.append(entry)
                else:
                    print(f"🔁 Duplicate log skipped: {fingerprint}")

            if new_entries:
                print(f"✅ Found {len(new_entries)} new log entry(ies) to broadcast.")
                await self.broadcast_log_entries(new_entries)
            else:
                print("ℹ️ No new OpenClaw log entries.")

            print(f"💤 Sleeping for {LOG_POLL_INTERVAL_SECONDS} seconds before next log poll.")
            await asyncio.sleep(LOG_POLL_INTERVAL_SECONDS)

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
        media_path = None
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
                print(f"🔁 Initial sync status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    self.sync_token = data.get("next_batch")
                    self.update_joined_rooms(data)
                    print(f"🚀 Ready! Joined rooms: {len(self.joined_rooms)}")
                    watcher_task = asyncio.create_task(self.openclaw_log_watcher())
                    print("🚀 OpenClaw log watcher task started.")
                else:
                    print(f"❌ Error during initial sync: {resp.status}")
                    return

            while True:
                try:
                    url = f"{HOMESERVER}/_matrix/client/r0/sync?timeout=30000"
                    if self.sync_token:
                        url += f"&since={self.sync_token}"
                    
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=45)) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.sync_token = data.get("next_batch")
                            self.update_joined_rooms(data)
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