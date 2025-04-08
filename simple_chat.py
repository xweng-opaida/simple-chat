import io
import traceback
import time
from openai import OpenAI
import base64
import os
import datetime
import uuid
from dotenv import load_dotenv
import logging
import shutil
from PIL import Image
from utils import resize_image
from collections import defaultdict
import tempfile
import json  # Import the json module
from flask import Flask, request, jsonify, send_from_directory

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
last_reset_date = datetime.date.today()

# Configure OpenAI client
client = OpenAI(
    base_url=os.getenv('OPENAI_BASE_URL'),
    api_key=os.getenv('OPENAI_API_KEY'),
)
MODEL_NAME = os.getenv('MODEL_NAME')

app = Flask(__name__)

# Serve static files (index.html, script.js)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/chat', methods=['POST'])
def chat():
    global ip_upload_counts, last_reset_date
    data = request.get_json()
    message = data.get('message', '')
    camera_data = data.get('image', '')
    history = data.get('history', []) # Get the history from the request
    ip = request.remote_addr
    current_date = datetime.date.today()

    # Reset daily upload counts
    if current_date != last_reset_date:
        logger.info(f"New day detected ({current_date}). Resetting upload counts.")
        ip_upload_counts.clear()
        last_reset_date = current_date

    logger.info(f"Chat request from IP: {ip}. Current count: {ip_upload_counts[ip]}")

    files_to_process = []
    num_files_in_message = 0

    # Handle Base64 camera data
    camera_file_path = None
    if camera_data and camera_data.startswith("data:image"):
        try:
            logger.info("Processing Base64 camera data...")
            header, encoded = camera_data.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            extension = mime_type.split("/")[-1] or "png"

            image_data = base64.b64decode(encoded)

            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
                temp_file.write(image_data)
                camera_file_path = temp_file.name
            logger.info(f"Camera image saved temporarily to {camera_file_path}")
            files_to_process.append(camera_file_path)
            num_files_in_message = 1  # Treat camera upload as one file
        except Exception as e:
            logger.exception(f"Error processing Base64 camera data: {e}")
            return jsonify({"response": "Sorry, there was an error processing the camera photo."})

    # Check upload limit
    if num_files_in_message > 0 and ip_upload_counts[ip] + num_files_in_message > UPLOAD_LIMIT:
        logger.warning(f"Upload attempt rejected for IP {ip}. Limit: {UPLOAD_LIMIT}, Current: {ip_upload_counts[ip]}, Attempted: {num_files_in_message}")
        if camera_file_path:
            try:
                os.remove(camera_file_path)
                logger.info(f"Cleaned up rejected temp camera file: {camera_file_path}")
            except OSError as e:
                logger.error(f"Error removing temp camera file {camera_file_path}: {e}")
            return jsonify({"response": f"Sorry, you can only upload {UPLOAD_LIMIT} images per day. You have already uploaded {ip_upload_counts[ip]} today."})

    # Process files (only camera uploads for now) and store the new path
    new_file_path = None # Initialize new_file_path
    for file_path in files_to_process:
        try:
            filename, ext = os.path.splitext(os.path.basename(file_path))
            unique_filename = f"{filename}_{uuid.uuid4()}{ext}"
            upload_dir = os.path.join("uploads", current_date.strftime("%Y-%m-%d"))
            os.makedirs(upload_dir, exist_ok=True)
            new_file_path = os.path.join(upload_dir, unique_filename)
            # Move the file to the new directory using shutil.move for cross-device compatibility
            shutil.move(file_path, new_file_path)
            history.append({"role": "user", "content": {"path": new_file_path}})
        except Exception as e:
            logger.exception(f"Error moving file: {e}")
            return jsonify({"response": f"Error processing file upload."})

    # Prepare messages for OpenAI, starting with history
    # Ensure history items are valid dictionaries with 'role' and 'content'
    processed_history = [item for item in history if isinstance(item, dict) and 'role' in item and 'content' in item]
    logger.info(f"Received history with {len(processed_history)} items.")

    # If a new image was uploaded in this request, filter out previous image messages from history
    if new_file_path: # Check if a new image was processed
        logger.info("New image uploaded. Filtering previous images from history.")
        filtered_history = []
        for item in processed_history:
            contains_image = False
            if isinstance(item.get('content'), list):
                for part in item['content']:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        contains_image = True
                        break
            if not contains_image:
                filtered_history.append(item)
            else:
                logger.debug(f"Filtering out history item with image: {item.get('role')}")
        messages = filtered_history
        logger.info(f"History filtered. Kept {len(messages)} non-image items.")
    else:
        messages = processed_history # Use the original history if no new image

    # Prepare current user message content (text and/or image)
    current_user_content = []
    if message:
        current_user_content.append({"type": "text", "text": message})

    if camera_data and new_file_path: # Check if camera data and processed file path exist
        try:
            logger.info(f"Processing image {new_file_path} for API call.")
            with open(new_file_path, "rb") as image_file:
                img = Image.open(io.BytesIO(image_file.read()))
                # Resize if needed (assuming resize_if_needed handles potential errors)
                resized_img = resize_image(img)
                img_buffer = io.BytesIO()
                # Determine format based on original extension or default to PNG
                original_format = img.format if img.format else "PNG"
                resized_img.save(img_buffer, format=original_format)
                encoded_string = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                # Determine mime type based on format
                mime_type = Image.MIME.get(original_format.upper(), "image/png")
                current_user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{encoded_string}"}
                })
                logger.info(f"Image added to current message content (format: {original_format}).")
        except Exception as e:
            logger.error(f"Error processing image {new_file_path} for API: {e}")
            logger.error(traceback.format_exc())
            # Don't immediately return, maybe the text part is still useful
            # return jsonify({"response": f"Error processing image for the AI model."})
            # Instead, maybe add an error message to the chat? Or just log it.
            # For now, just log and proceed without the image in the API call.
            pass # Continue without the image if processing failed

    # Add the current user message (potentially with image) to the messages list
    if current_user_content:
        messages.append({"role": "user", "content": current_user_content})
    elif not messages: # If history was empty AND no new message/image
         logger.warning("No history and no current message/image content.")
         return jsonify({"response": "Please provide a message or image."}) # Or handle as appropriate

    # Call OpenAI API
    try:
        logger.info(f"Calling OpenAI API with {len(messages)} messages.")
        # Log the structure of the last message for debugging multi-modal issues
        if messages:
            logger.debug(f"Last message structure: {messages[-1]}")

        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=True,  # Enable streaming
        )

        def generate():
            with app.app_context():
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield json.dumps({"response": chunk.choices[0].delta.content}).encode('utf-8')

        return generate()

    except Exception as e:
        logger.error(f"An error occurred during API call: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"response": f"An error occurred while contacting the AI model: {str(e)}"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8100, debug=True)
