    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const cameraInput = document.getElementById('camera-input');
    const cameraButton = document.getElementById('camera-button');
    const uploadInput = document.getElementById('upload-input'); // Added
    const uploadButton = document.getElementById('upload-button'); // Added
    const cameraData = document.getElementById('camera-data'); // Will reuse for uploads
    const uploadedImage = document.getElementById('uploaded-image');
    const imageContainer = document.getElementById('image-container');

let imageAspectRatio = 1; // Default aspect ratio
let chatHistory = []; // Array to store chat history

uploadedImage.onload = () => {
    imageAspectRatio = uploadedImage.naturalWidth / uploadedImage.naturalHeight;
};

document.addEventListener('DOMContentLoaded', () => {
    messageInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    cameraButton.addEventListener('click', () => {
        cameraInput.click();
    });

    // Event listener for the new upload button
    uploadButton.addEventListener('click', () => {
        uploadInput.click();
    });

    // Event listener for the hidden upload input
    uploadInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                // Reuse cameraData to store the image data URL
                cameraData.value = e.target.result;
                // Display the selected image in the top container
                uploadedImage.src = e.target.result;
                imageContainer.style.display = "block";
                sendMessage(); // Automatically send the message with the uploaded image
            };
            reader.readAsDataURL(file);
        }
    });

    // Event listener for the camera input
    cameraInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                cameraData.value = e.target.result;
                uploadedImage.src = e.target.result; // Display image in the top section
                imageContainer.style.display = "block"; // Show the image container
                sendMessage(); 

            };
            reader.readAsDataURL(file);
        }
    });

    function sendMessage() {
        const message = messageInput.value;
        const imageData = cameraData.value;

        if (message || imageData) {
            // Add user message to history
            const userMessageEntry = { role: 'user', content: message };
            if (imageData) {
                // If there's an image, structure content for multimodal input
                userMessageEntry.content = []; // Initialize content as an array
                if (message) { // Add text part if it exists
                    userMessageEntry.content.push({ type: "text", text: message });
                }
                // Add the image part in the format expected by the API history
                userMessageEntry.content.push({
                    type: "image_url",
                    image_url: { "url": imageData } // Use the base64 data URL
                });
                 // Display user message (including image)
                displayMessage('user', message, imageData);
            } else {
                 // Only text message
                 userMessageEntry.content = message; // Keep simple string content for text-only
                 displayMessage('user', message);
            }
            // Add the potentially multimodal entry to history
            chatHistory.push(userMessageEntry);


            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                // Send message, image, and history (filter out image messages from history)
                body: JSON.stringify({
                    message: message,
                    image: imageData,
                    // Filter history to exclude messages with array content (images)
                    history: chatHistory.slice(-6).filter(entry => !Array.isArray(entry.content))
                })
            })
            .then(response => {
                const reader = response.body.getReader();
                let partialResponse = "";
                let botMessageElement = document.createElement('div');
                botMessageElement.classList.add('bot-message');
                chatWindow.appendChild(botMessageElement);
                let jsonBuffer = ""; // Buffer for potentially incomplete JSON chunks

                function processStream() {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            // Stream finished - process any remaining buffer content if needed
                            // (Usually, the buffer should be empty if JSONs were well-formed)
                            if (jsonBuffer.trim()) {
                                console.warn("Stream finished with non-empty JSON buffer:", jsonBuffer);
                                // Attempt a final parse or display the raw buffer as fallback
                                try {
                                     // This final parse might be problematic if buffer is truly corrupt
                                     const jsonChunk = JSON.parse(jsonBuffer);
                                     if (jsonChunk.response) {
                                         partialResponse += jsonChunk.response;
                                     } else {
                                         partialResponse += jsonBuffer; // Fallback
                                     }
                                } catch (e) {
                                     partialResponse += jsonBuffer; // Fallback: append raw remaining buffer
                                }
                            }
                            // Update display with final content
                            botMessageElement.innerHTML = marked.parse(partialResponse);
                            chatWindow.scrollTop = chatWindow.scrollHeight;
                            // Add complete bot response to history
                            if (partialResponse) { // Only add if there's content
                                chatHistory.push({ role: 'assistant', content: partialResponse });
                            }
                            return;
                        }

                        const textDecoder = new TextDecoder();
                        jsonBuffer += textDecoder.decode(value, { stream: true }); // Append new chunk to buffer

                        // Process buffer to extract complete JSON objects
                        let boundaryIndex;
                        // Assuming backend sends distinct JSON objects like {"response": "..."}
                        // A simple approach is to look for '}' which usually ends the object.
                        // More robust: Find JSON start '{' and matching '}'
                        while ((boundaryIndex = jsonBuffer.indexOf('}')) !== -1) {
                            const potentialJson = jsonBuffer.substring(0, boundaryIndex + 1);
                            try {
                                const jsonChunk = JSON.parse(potentialJson);
                                if (jsonChunk && jsonChunk.response !== undefined) {
                                    partialResponse += jsonChunk.response; // Append content
                                    botMessageElement.innerHTML = marked.parse(partialResponse); // Update display
                                    chatWindow.scrollTop = chatWindow.scrollHeight;
                                } else {
                                     console.warn("Parsed JSON chunk missing 'response':", jsonChunk);
                                }
                                jsonBuffer = jsonBuffer.substring(boundaryIndex + 1); // Remove processed part
                            } catch (e) {
                                // JSON incomplete or malformed, break and wait for more data
                                // console.warn("Incomplete JSON in buffer, waiting for more data:", potentialJson, e);
                                break;
                            }
                        }

                        processStream(); // Continue reading the stream
                    });
                }

                processStream(); // Start processing the stream
            })
            .catch(error => {
                console.error('Error:', error);
            });

            messageInput.value = '';
            cameraData.value = '';
            // Keep the image displayed in the top container after sending
            // uploadedImage.src = ""; // Clear the image after sending
            // imageContainer.style.display = "none"; // Hide the image container
        }
    }

    // Updated displayMessage to handle potential images for user messages
    function displayMessage(sender, message, imageData = null) {
        const messageElement = document.createElement('div');
        messageElement.classList.add(sender + '-message'); // e.g., 'user-message'

        let contentHTML = '';
        if (message) {
            // Use marked.parse for user messages too for consistency (e.g., markdown links)
            contentHTML += marked.parse(message);
        }

        // If it's a user message and there's image data, display the image *below* the text
        if (sender === 'user' && imageData) {
            const imgElement = document.createElement('img');
            imgElement.src = imageData;
            imgElement.style.maxWidth = '80%'; // Limit image width in chat
            imgElement.style.maxHeight = '200px'; // Limit image height
            imgElement.style.marginTop = '5px'; // Add some space
            imgElement.style.display = 'block'; // Ensure it's on its own line
            // Append image HTML after text HTML
            // We need to append the image element itself, not its HTML string yet
             messageElement.innerHTML = contentHTML; // Set text first
             messageElement.appendChild(imgElement); // Then append the image element
        } else {
             messageElement.innerHTML = contentHTML; // Just set the text if no image
        }


        chatWindow.appendChild(messageElement);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Drag divider
    const divider = document.getElementById('divider');
    // Use existing imageContainer and chatWindow variables from the top scope
    let isDragging = false;

    divider.addEventListener('mousedown', (e) => {
        isDragging = true;
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', () => {
            isDragging = false;
            document.removeEventListener('mousemove', drag);
        });
    });

    function drag(e) {
        if (!isDragging) return;

        // Calculate new height for image container
        let newHeight = e.clientY - imageContainer.offsetTop;

        // Set a minimum and maximum height
        const minHeight = 50;
        const maxHeight = chatWindow.offsetHeight + imageContainer.offsetHeight - 50;
        newHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));

        imageContainer.style.height = newHeight + 'px';
        uploadedImage.style.height = newHeight + 'px';
        chatWindow.style.height = (chatWindow.offsetHeight + imageContainer.offsetHeight - newHeight) + 'px';
    }
});
