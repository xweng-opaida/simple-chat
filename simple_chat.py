import io
import traceback
import gradio as gr
import time
from openai import OpenAI
import base64
import os
import datetime
import uuid
from dotenv import load_dotenv
import logging
from PIL import Image
from utils import resize_if_needed
from collections import defaultdict
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# IP-based image upload limit - read from environment variable, default to 2
try:
    UPLOAD_LIMIT = int(os.getenv('UPLOAD_LIMIT', '2'))
except ValueError:
    logger.warning("Invalid UPLOAD_LIMIT in .env file, defaulting to 2.")
    UPLOAD_LIMIT = 2
ip_upload_counts = defaultdict(int)
last_reset_date = datetime.date.today() # Track the date for daily reset

# Chatbot demo with multimodal input (text, markdown, LaTeX, code blocks, image, audio, & video). Plus shows support for streaming text.

# Configure OpenAI client
client = OpenAI(
    base_url=os.getenv('OPENAI_BASE_URL'),
    api_key=os.getenv('OPENAI_API_KEY'),
)
MODEL_NAME = os.getenv('MODEL_NAME')


def print_like_dislike(x: gr.LikeData):
    print(x.index, x.value, x.liked)


def add_message(history, message, request: gr.Request):
    global ip_upload_counts, last_reset_date
    ip = request.client.host
    current_date = datetime.date.today()

    # Check if the date has changed since the last reset
    if current_date != last_reset_date:
        logger.info(f"New day detected ({current_date}). Resetting upload counts.")
        ip_upload_counts.clear()
        last_reset_date = current_date

    logger.info(f"Adding message from IP: {ip}. Current count: {ip_upload_counts[ip]}")

    num_files_in_message = len(message["files"]) if message["files"] else 0

    # Check if adding these files exceeds the limit
    if num_files_in_message > 0 and ip_upload_counts[ip] + num_files_in_message > UPLOAD_LIMIT:
        logger.warning(f"Upload attempt rejected for IP {ip}. Limit: {UPLOAD_LIMIT}, Current: {ip_upload_counts[ip]}, Attempted: {num_files_in_message}")
        history.append({
            "role": "assistant",
            "content": f"Sorry, you can only upload {UPLOAD_LIMIT} images per day. You have already uploaded {ip_upload_counts[ip]} today."
        })
        # Keep input active, clear the attempted message
        return history, gr.MultimodalTextbox(value=None, interactive=True)

    # If limit is not exceeded, proceed with processing the message
    upload_dir = os.path.join("uploads", current_date.strftime("%Y-%m-%d"))
    os.makedirs(upload_dir, exist_ok=True)

    for file_path in message["files"]:
        try:
            # Get the filename and extension from the path
            filename, ext = os.path.splitext(os.path.basename(file_path))
            # Generate a unique filename
            unique_filename = f"{filename}_{uuid.uuid4()}{ext}"
            # Create the new file path
            new_file_path = os.path.join(upload_dir, unique_filename)
            # Move the file to the new directory
            os.rename(file_path, new_file_path)  # Rename (move) the file
            history.append({"role": "user", "content": {"path": new_file_path}})
        except Exception as e:
            logger.exception(f"Error moving file: {e}")
            history.append({"role": "user", "content": {"path": file_path}})  # Append original path if move fails

    if message["text"] is not None:
        history.append({"role": "user", "content": message["text"]})

    # Increment count only after successful processing
    ip_upload_counts[ip] += num_files_in_message
    logger.info(f"Message added for IP {ip}. New count: {ip_upload_counts[ip]}")

    # Clear input after successful submission
    return history, gr.MultimodalTextbox(value=None, interactive=False)


def bot(history: list):
    logger.info("Processing bot response")
    # Format history for OpenAI API
    messages = []
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        if isinstance(content, tuple):
            image_path = content[0]
            try:
                with open(image_path, "rb") as image_file:
                    img = Image.open(io.BytesIO(image_file.read()))
                    resized_img = resize_if_needed(img)
                    img_buffer = io.BytesIO()
                    resized_img.save(img_buffer, format="PNG")
                    encoded_string = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                messages.append({"role": role, "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}]})
            except Exception as e:
                logger.error(f"Error reading image: {str(e)}")
                logger.error(traceback.format_exc())
                messages.append({"role": role, "content": f"Error reading image: {str(e)}"})
        elif isinstance(content, str):
            messages.append({"role": role, "content": content})

    if not messages: # Handle case where only files were uploaded
        history.append({"role": "assistant", "content": "Sorry, I can only process text messages for now."})
        yield history
        return

    history.append({"role": "assistant", "content": ""})
    try:
        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                history[-1]["content"] += chunk.choices[0].delta.content
                yield history
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        history[-1]["content"] = f"An error occurred: {str(e)}"
        yield history


with gr.Blocks(css="footer {visibility: hidden}",title="opAIda Chat") as demo:
    chatbot = gr.Chatbot(elem_id="chatbot", bubble_full_width=False, type="messages")

    chat_input = gr.MultimodalTextbox(
        interactive=True,
        file_count="multiple",
        placeholder="Enter message or upload file...",
        show_label=False,
        sources=[
            # "microphone", 
            "upload"],
    )

    # The gr.Request object is implicitly passed to add_message if it's in the function signature
    chat_msg = chat_input.submit(
        add_message, [chatbot, chat_input], [chatbot, chat_input]
    )
    bot_msg = chat_msg.then(bot, chatbot, chatbot, api_name="bot_response")
    bot_msg.then(lambda: gr.MultimodalTextbox(interactive=True), None, [chat_input])

    # chatbot.like(print_like_dislike, None, None, like_user_message=True)

demo.launch(
    server_name="0.0.0.0",
    server_port=8100,
    favicon_path="icon.png",
    )
