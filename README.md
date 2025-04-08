# opAIda Chat

This project is a simple chat application.

## Setup

1.  **Install dependencies:**

    ```bash
    pip install gradio openai python-dotenv pdf2image
    ```
2.  **Configure Environment Variables:**

    Copy the `.env.example` file to a new file named `.env`:

    ```bash
    cp .env.example .env
    ```

    Then, edit the `.env` file with your specific configuration:

    *   `OPENAI_BASE_URL`: The base URL for your OpenAI-compatible API endpoint.
    *   `OPENAI_API_KEY`: Your API key for the service.
    *   `MODEL_NAME`: The specific model you want to use.
    *   `UPLOAD_LIMIT`: (Optional) The maximum number of images a user can upload per day (based on IP address). Defaults to 2 if not set.

3.  **Run the script:**

    ```bash
    python simple_chat.py
    ```

    This will start the Gradio interface, which you can access in your browser. The interface will be running on port 8100.

## Files

*   `simple_chat.py`: Main script for the chat application using Gradio and OpenAI.
*   `utils.py`: Contains utility functions (e.g., image resizing).
*   `icon.png`: Favicon for the Gradio interface.
*   `.env.example`: Example environment variable configuration file.
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore (like `.env` and `uploads/`).

## Specifications

*   **Framework:** Gradio
*   **Language Model:** OpenAI-compatible API (configurable via `.env`)
*   **Features:**
    *   Text chat with streaming responses.
    *   Multi-modal input (text and image uploads).
    *   Daily image upload limit per user (IP-based, configurable via `UPLOAD_LIMIT` in `.env`).
    *   Uploaded images are stored in the `uploads/` directory, organized by date.
