import os, httpx

key = os.environ.get("OPENAI_API_KEY", "")
print(f"Raw key repr: {repr(key[:30])}")
key = key.strip()
print(f"Stripped key length: {len(key)}")

if not key:
    print("ERROR: key is empty")
    exit(1)

print("Calling OpenAI TTS...")
response = httpx.post(
    "https://api.openai.com/v1/audio/speech",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": "tts-1", "input": "Bonjour. Première Intelligence. Test audio.", "voice": "nova"},
    timeout=30,
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    os.makedirs("audio", exist_ok=True)
    with open("audio/test.mp3", "wb") as f:
        f.write(response.content)
    print("✓ Audio saved to audio/test.mp3")
else:
    print(f"ERROR: {response.text}")
    exit(1)
