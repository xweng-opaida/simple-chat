    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const cameraInput = document.getElementById('camera-input');
    const cameraButton = document.getElementById('camera-button');
    const uploadInput = document.getElementById('upload-input'); // Added
    const uploadButton = document.getElementById('upload-button'); // Added
    const cameraData = document.getElementById('camera-data'); // Will reuse for uploads
    const uploadedImage = document.getElementById('uploaded-image');
    const imageContainer = document.getElementById('image-container');
    const initialBotMessageElement = document.getElementById('initial-bot-message'); // Get the initial message element
    const clearChatButton = document.getElementById('clear-chat-button'); // Added Clear Chat Button

let imageAspectRatio = 1; // Default aspect ratio
let chatHistory = []; // Array to store chat history
let uploadLimit = null; // Store the upload limit
let currentUploadCount = 0; // Store the current upload count

uploadedImage.onload = () => {
    imageAspectRatio = uploadedImage.naturalWidth / uploadedImage.naturalHeight;
};

// Function to animate typing effect
function typeWriter(element, text, speed = 1) {
    let i = 0;
    element.innerHTML = ''; // Clear initial text
    const lines = text.split('\n');

    function typeLine(lineIndex) {
        if (lineIndex < lines.length) {
            const line = lines[lineIndex];
            let charIndex = 0;
            const lineElement = document.createElement('span');
            element.appendChild(lineElement);

            function typeChar() {
                if (charIndex < line.length) {
                    lineElement.textContent += line.charAt(charIndex);
                    charIndex++;
                    setTimeout(typeChar, speed);
                } else {
                    const br = document.createElement('br');
                    element.appendChild(br);
                    typeLine(lineIndex + 1);
                }
            }
            typeChar();
        }
    }
    typeLine(0);
}

// Updated displayMessage to handle potential images for user messages
// Moved to global scope to be accessible by checkUploadLimitAndProceed
function displayMessage(sender, message, imageData = null) {
    const messageElement = document.createElement('div');
    messageElement.classList.add(sender + '-message'); // e.g., 'user-message'

    let contentHTML = '';
    if (message) {
        // Use marked.parse for user messages too for consistency (e.g., markdown links)
        // Ensure marked is loaded before this function is called if used here
        // For simplicity, let's assume marked is globally available or handle its loading.
        // If marked is only used within sendMessage, this is fine.
        // If used here, ensure marked.parse is safe to call.
        // Let's stick to basic text for the bot message here to avoid marked dependency outside sendMessage
        if (sender === 'bot') {
             contentHTML = message; // Display plain text for bot messages from this function
        } else {
             // Assuming marked is available for user messages if needed, or just use text
             contentHTML = message; // Or marked.parse(message) if safe
        }
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
         // messageElement.appendChild(imgElement); // Then append the image element
    } else {
         messageElement.innerHTML = contentHTML; // Just set the text if no image
    }


    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Function to fetch and update upload status
async function fetchUploadStatus() {
     try {
         const response = await fetch('/upload_status');
         if (!response.ok) {
             throw new Error(`HTTP error! status: ${response.status}`);
         }
         const data = await response.json();
         uploadLimit = data.limit;
         currentUploadCount = data.current_count;
         console.log(`Upload status updated: Limit=${uploadLimit}, Count=${currentUploadCount}`);
     } catch (error) {
         console.error("Error fetching upload status:", error);
         // Optionally inform the user or disable uploads if status check fails critically
         // displayMessage('bot', "Could not verify upload status. Uploads may be limited.");
     }
 }


document.addEventListener('DOMContentLoaded', () => {
    // Fetch initial upload status
    fetchUploadStatus();

    // Animate the initial bot message
    if (initialBotMessageElement) {
        const initialText = initialBotMessageElement.textContent.replace(/<br\s*[\/]?>/gi, '\n');
        initialBotMessageElement.classList.add('hidden'); // Hide initially
        typeWriter(initialBotMessageElement, initialText);
        setTimeout(() => {
            initialBotMessageElement.classList.remove('hidden'); // Show after a delay
        }, 100); // Adjust delay as needed
    }

    messageInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    cameraButton.addEventListener('click', () => {
        if (uploadLimit !== null && currentUploadCount >= uploadLimit) {
            displayMessage('bot', `Image upload limit (${uploadLimit}) reached. Only text messages are allowed.`);
        } else {
            cameraInput.click();
        }
    });

    // Event listener for the new upload button
    uploadButton.addEventListener('click', () => {
         if (uploadLimit !== null && currentUploadCount >= uploadLimit) {
            displayMessage('bot', `Image upload limit (${uploadLimit}) reached. Only text messages are allowed.`);
        } else {
            uploadInput.click();
        }
    });

    // Event listener for the hidden upload input
    uploadInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            // Clear previous conversation when a new image is uploaded
            chatHistory = []; // Reset the history array
            chatWindow.innerHTML = ''; // Clear the visual chat window

            const reader = new FileReader();
            reader.onload = (e) => {
                // Reuse cameraData to store the image data URL
                cameraData.value = e.target.result;
                // Display the selected image in the top container
                uploadedImage.src = e.target.result;
                imageContainer.style.display = "block";
                currentUploadCount++; // Increment count when image is selected
                console.log(`Upload count incremented to: ${currentUploadCount}`);
                messageInput.value = "Tell me about the picture"; // Set the message
                sendMessage(); // Automatically send the message with the uploaded image
            };
            reader.readAsDataURL(file);
        }
    });

    // Event listener for the camera input
    cameraInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            chatHistory = []; // Reset the history array
            chatWindow.innerHTML = ''; // Clear the visual chat window
            const reader = new FileReader();
            reader.onload = (e) => {
                cameraData.value = e.target.result;
                uploadedImage.src = e.target.result; // Display image in the top section
                imageContainer.style.display = "block"; // Show the image container
                currentUploadCount++; // Increment count when image is selected
                console.log(`Upload count incremented to: ${currentUploadCount}`);
                messageInput.value = "Tell me about the picture"; // Set the message
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
                    // Send the full, unmodified chat history
                    history: chatHistory
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

            // Clear message input and only the image *data* after sending
            messageInput.value = '';
            cameraData.value = ''; // Clear the stored image data so it's not sent again
            // Keep the image preview visible in the UI:
            // uploadedImage.src = ""; // DO NOT clear the preview source
            // imageContainer.style.display = "none"; // DO NOT hide the container
        }
    }


    // Drag divider
    const divider = document.getElementById('divider');
    // Use existing imageContainer and chatWindow variables from the top scope
    let isDragging = false;

    // --- Mouse Events ---
    divider.addEventListener('mousedown', (e) => {
        isDragging = true;
        // Prevent default text selection behavior during drag
        e.preventDefault();
        document.addEventListener('mousemove', handleDragMove);
        document.addEventListener('mouseup', handleDragEnd);
    });

    // --- Touch Events ---
    divider.addEventListener('touchstart', (e) => {
        isDragging = true;
        // Prevent default touch behavior like scrolling
        e.preventDefault();
        document.addEventListener('touchmove', handleDragMove, { passive: false }); // Use passive: false if preventDefault is needed inside handler
        document.addEventListener('touchend', handleDragEnd);
    });

    function handleDragMove(e) {
        if (!isDragging) return;
        // Prevent scrolling during drag on touch devices
        if (e.type === 'touchmove') {
            e.preventDefault();
        }
        drag(e); // Pass the event object to drag
    }

    function handleDragEnd() {
        if (isDragging) { // Only remove listeners if we were actually dragging
            isDragging = false;
            document.removeEventListener('mousemove', handleDragMove);
            document.removeEventListener('mouseup', handleDragEnd);
            document.removeEventListener('touchmove', handleDragMove);
            document.removeEventListener('touchend', handleDragEnd);
        }
    }


    function drag(e) {
        // No need for the isDragging check here as handleDragMove already does it
        // if (!isDragging) return; // Removed

        // Get the parent container (assuming it's the direct parent of imageContainer and chatWindow)
        const parentContainer = imageContainer.parentElement;
        if (!parentContainer) return; // Safety check
        const totalHeight = parentContainer.clientHeight; // Use clientHeight for inner height

        // Determine the Y coordinate based on event type
        let pageY;
        if (e.type === 'touchmove') {
            // For touch events, use the first touch point
            if (e.touches && e.touches.length > 0) {
                pageY = e.touches[0].pageY;
            } else {
                // Fallback or error handling if no touch points are found
                return; // Exit if touch data is missing
            }
        } else {
            // For mouse events, use pageY directly
            pageY = e.pageY;
        }


        // Calculate new height for image container based on coordinate relative to parent
        let dividerTopRelativeToParent = pageY - parentContainer.getBoundingClientRect().top - window.scrollY;


        // Set a minimum height for the image container and the chat window
        const minImageHeight = 50; // Minimum height for the image area
        const minChatHeight = 100; // Minimum height for the chat area

        // Calculate the new height based on the divider position
        let newHeight = dividerTopRelativeToParent; // The top of the image container is 0 relative to parent

        // Calculate maximum possible height for the image container
        const maxHeight = totalHeight - minChatHeight - divider.offsetHeight; // Subtract min chat height and divider height

        // Clamp the new height within the calculated bounds
        newHeight = Math.max(minImageHeight, Math.min(maxHeight, newHeight));

        // Calculate the corresponding chat window height
        const newChatHeight = totalHeight - newHeight - divider.offsetHeight;

        // Apply the new heights
        imageContainer.style.height = newHeight + 'px';
        chatWindow.style.height = newChatHeight + 'px';

        // Remove direct image height setting - let CSS handle it
        // uploadedImage.style.height = newHeight + 'px'; // REMOVED
    }

    // Event listener for the clear chat button
    clearChatButton.addEventListener('click', () => {
        // Find the first user message that contains an image
        const imageMessageEntry = chatHistory.find(entry =>
            entry.role === 'user' &&
            Array.isArray(entry.content) &&
            entry.content.some(item => item.type === 'image_url')
        );

        // Clear the chat window visually
        chatWindow.innerHTML = '';

        // Reset chat history to only contain the image message, or be empty
        chatHistory = imageMessageEntry ? [imageMessageEntry] : [];

        // If an image message exists, re-display it
        if (imageMessageEntry) {
            // Extract text and image data for displayMessage
            const textContent = imageMessageEntry.content.find(item => item.type === 'text')?.text || '';
            const imageUrl = imageMessageEntry.content.find(item => item.type === 'image_url')?.image_url.url;
            if (imageUrl) { // Ensure we have an image URL before displaying
                 displayMessage('user', textContent, imageUrl);
            }
        }
        // Optionally, re-add the initial bot message if needed and no image is present
        // else {
        //     const initialMessageDiv = document.createElement('div');
        //     initialMessageDiv.classList.add('bot-message');
        //     initialMessageDiv.id = 'initial-bot-message'; // Re-assign ID if needed elsewhere
        //     initialMessageDiv.textContent = "Got a document? Just snap a pic and ask away — opAIda's here to help!";
        //     chatWindow.appendChild(initialMessageDiv);
        //     typeWriter(initialMessageDiv, initialMessageDiv.textContent); // Re-animate if desired
        // }


        console.log("Chat history cleared, preserving image message if present.");
    });
});
