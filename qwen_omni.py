import base64
import mimetypes
import os
import argparse
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY_KEY"
)

def encode_audio_to_base64(audio_path):
    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/wav"
    with open(audio_path, "rb") as audio_file:
        encoded = base64.b64encode(audio_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"

def send_audio_via_chat_completions(audio_path, prompt):
    base64_audio = encode_audio_to_base64(audio_path)

    messages = [
        {
            "role": "system",
            "content": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "audio_url",
                    "audio_url": {
                        "url": base64_audio
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]

    print("�~_�~V Qwen (chat.completions): ", end="", flush=True)
    response = client.chat.completions.create(
        model="Qwen2.5-Omni-7B",
        messages=messages,
        stream=True
    )

    for chunk in response:
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", "")
        print(content, end="", flush=True)
    print()

def main():
    parser = argparse.ArgumentParser(description="Test /v1/chat/completions with audio base64 input")
    parser.add_argument("audio_path", help="Path to audio file (.wav or .mp3)")
    parser.add_argument("--prompt", default="Please transcribe the audio and return the speech as text.", help="Prompt to send")

    args = parser.parse_args()
    audio_path = args.audio_path

    if not os.path.exists(audio_path):
        print("�~]~L File not found.")
        return

    send_audio_via_chat_completions(audio_path, args.prompt)

if __name__ == "__main__":
    main()