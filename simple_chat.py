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
import json
import hashlib # Import hashlib for hashing
from flask import Flask, request, jsonify, send_from_directory

load_dotenv()
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set to store hashes of already saved images to prevent duplicates within the same day
saved_image_hashes = set()

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
    global ip_upload_counts, last_reset_date, saved_image_hashes # Add saved_image_hashes here
    data = request.get_json()
    # message = data.get('message', '') # Removed
    # camera_data = data.get('image', '') # Removed
    history = data.get('history', []) # Get the history from the request
    ip = request.remote_addr
    current_date = datetime.date.today()

    # Reset daily limits and saved image hashes
    if current_date != last_reset_date:
        logger.info(f"New day detected ({current_date}). Resetting daily limits and saved image hashes.")
        ip_upload_counts.clear()
        saved_image_hashes.clear() # Clear the saved hashes set
        last_reset_date = current_date

    logger.info(f"Chat request from IP: {ip}. Current count: {ip_upload_counts[ip]}")

    # Removed code block handling camera_data, upload limits, and file processing for new images

    # Prepare messages for OpenAI, starting with history
    # Ensure history items are valid dictionaries with 'role' and 'content'
    processed_history = [item for item in history if isinstance(item, dict) and 'role' in item and 'content' in item]
    logger.info(f"Received history with {len(processed_history)} items.")

    # Initialize messages with the processed history received from the frontend
    messages = processed_history

    # Define the system prompt
    system_prompt = """Analyze the provided document image, which may include handwritten notes, printed text, forms, or mixed media. Structure your response as follows:


output all text content in the image


"""

    # Prepend the system prompt to the messages list
    messages.insert(0, {"role": "system", "content": system_prompt})
    logger.info("Prepended system prompt to messages.")


    # Removed code block preparing/appending current user message content (text/image)

    # Check if there's any history to process after filtering
    if not messages:
        logger.warning("No valid history provided in the request.")
        # Return an error or appropriate response if history is empty
        return jsonify({"response": "No chat history provided or history is invalid."})

    # --- Resize images already present in the history before sending to API ---
    # The code above handles resizing for NEWLY uploaded images (`camera_data`).
    # This loop ensures images passed from the client as part of the `history` are also resized.
    logger.info("Checking history messages for images to resize...")
    for i, msg in enumerate(messages):
        # Check if the message content is a list (potentially multi-modal)
        if isinstance(msg.get('content'), list):
            new_content_list = []
            image_resized_in_msg = False
            for content_part in msg['content']:
                # Check if this part is an image URL
                if content_part.get('type') == 'image_url':
                    image_url_data = content_part['image_url']['url']
                    # Check if it's a base64 encoded image
                    if image_url_data.startswith("data:image"):
                        try:
                            # Decode base64 image
                            header, encoded = image_url_data.split(",", 1)
                            mime_type = header.split(":")[1].split(";")[0]
                            image_data = base64.b64decode(encoded)

                            # --- Hash and Save Image (if unique for the day) ---
                            try:
                                image_hash = hashlib.sha256(image_data).hexdigest()
                                if image_hash not in saved_image_hashes:
                                    ip_upload_counts[ip] += 1
                                    img_for_saving = Image.open(io.BytesIO(image_data)) # Open image to get format
                                    original_format_save = img_for_saving.format if img_for_saving.format else mime_type.split('/')[-1].upper()
                                    if not original_format_save: original_format_save = "PNG"

                                    now = datetime.datetime.now()
                                    date_folder = now.strftime("%Y-%m-%d")
                                    upload_dir = os.path.join('uploads', date_folder)
                                    os.makedirs(upload_dir, exist_ok=True)

                                    timestamp = now.strftime("%Y%m%d_%H%M%S")
                                    unique_id = uuid.uuid4()
                                    filename = f"{timestamp}_{unique_id}.{original_format_save.lower()}"
                                    save_path = os.path.join(upload_dir, filename)

                                    with open(save_path, "wb") as f:
                                        f.write(image_data) # Save the original decoded data
                                    logger.info(f"Image from history (message index {i}, hash: {image_hash[:8]}...) saved to: {save_path}")
                                    saved_image_hashes.add(image_hash) # Add hash to set for today
                                else:
                                    logger.info(f"Duplicate image detected in history for today (message index {i}, hash: {image_hash[:8]}...). Skipping save.")

                            except Exception as save_e:
                                logger.error(f"Error saving image from history (message index {i}): {save_e}")
                                logger.error(traceback.format_exc())
                            # --- End Hash and Save ---

                            # Continue with preparing image for API
                            img = Image.open(io.BytesIO(image_data)) # Re-open for resizing
                            # Determine original format for API
                            original_format = img.format if img.format else mime_type.split('/')[-1].upper()
                            if not original_format: original_format = "PNG" # Default if still unknown

                            logger.info(f"Resizing image from history (message index {i}, format: {original_format})...")
                            # Resize using the imported utility function
                            resized_img = resize_image(img)
                            # Re-encode the resized image to base64
                            img_buffer = io.BytesIO()
                            resized_img.save(img_buffer, format=original_format)
                            encoded_string = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

                            # Create the updated content part with the resized image
                            new_content_list.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{encoded_string}"}
                            })
                            image_resized_in_msg = True
                        except Exception as e:
                            logger.error(f"Error resizing image from history (message index {i}): {e}")
                            logger.error(traceback.format_exc())
                            new_content_list.append(content_part) # Keep original image part if resizing failed
                    else:
                        # If it's an image_url but not base64 data, keep it as is
                        new_content_list.append(content_part)
                else:
                    # Keep non-image parts (like text) as they are
                    new_content_list.append(content_part)

            # If any image in this message was successfully resized, update the message's content
            if image_resized_in_msg:
                messages[i]['content'] = new_content_list
                logger.info(f"Finished resizing image(s) in history message {i}.")
        # else: If message content is not a list, it's likely just text, so no image processing needed for this message.

    # Call OpenAI API
    try:
        logger.info(f"Calling OpenAI API with {len(messages)} messages from history (images resized).")
        # Log the structure of the last message for debugging multi-modal issues
        if messages:
            logger.debug(f"Last message structure: {messages[-1]}")

        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=True,  # Enable streaming
            max_tokens=10000,
            top_p=0.4,  # make this smaller to return consistent result
            frequency_penalty=0.05,  # make this larger if you see unnecessary duplicated strings
            presence_penalty=0.0005,
            temperature=0.3  # make this value same as top_p
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

@app.route('/upload_status', methods=['GET'])
def upload_status():
    global ip_upload_counts, last_reset_date, saved_image_hashes # Ensure global access
    ip = request.remote_addr
    current_date = datetime.date.today()

    # Reset daily limits if it's a new day (important for accuracy if this endpoint is hit first)
    if current_date != last_reset_date:
        logger.info(f"New day detected ({current_date}) during status check. Resetting daily limits.")
        ip_upload_counts.clear()
        saved_image_hashes.clear() # Also clear hashes on reset
        last_reset_date = current_date
        # Note: We don't clear saved_image_hashes here as it's tied to the daily reset

    current_count = ip_upload_counts.get(ip, 0) # Use .get() for safety, default to 0
    limit = UPLOAD_LIMIT

    logger.info(f"Upload status request from IP: {ip}. Current count: {current_count}, Limit: {limit}")
    return jsonify({
        "current_count": current_count,
        "limit": limit
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8100, debug=True)
