let conversationId = "";
let uploadedFiles = [];
let isWaitingForResponse = false;

// Initialize chat directly when the page loads
document.addEventListener("DOMContentLoaded", () => {
    conversationId = "";
    document.getElementById("chat-box").innerHTML = "New chat started.";
    uploadedFiles = [];
    displayUploadedFiles();

    document.getElementById("message").removeAttribute("disabled");
    document.getElementById("message").focus();
    document.getElementById("sendbtn").removeAttribute("disabled");
});

function displayUploadedFiles() {
    const fileList = document.getElementById("files");
    fileList.innerHTML = ""; // Clear the list

    uploadedFiles.forEach((filename) => {
        const listItem = document.createElement("li");
        listItem.textContent = filename;
        fileList.appendChild(listItem);
    });
}

function disableInputs() {
    document.getElementById("message").setAttribute("disabled", "true");
    document.getElementById("sendbtn").setAttribute("disabled", "true");
}

function enableInputs() {
    document.getElementById("message").removeAttribute("disabled");
    document.getElementById("sendbtn").removeAttribute("disabled");
}

async function sendMessage() {
    const message = document.getElementById("message").value;
    const files = document.getElementById("upload-files").files;

    if (!message && files.length === 0) {
        alert("Please enter a message or select files to upload.");
        return;
    }
    
    // Disable inputs while processing
    disableInputs();
    isWaitingForResponse = true;

    document.getElementById(
        "chat-box"
    ).innerHTML += `<div class='message user'>User: ${message}</div>`;
    document.getElementById("message").value = "";

    const formData = new FormData();
    formData.append("message", message);

    if (files) {
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }
    }

    formData.append("conversation_id", conversationId);

    try {
        const response = await fetch("http://localhost:8000/chat", {
            method: "POST",
            body: formData,
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let chunk;
        let fullResponse = ""; // Accumulate the entire response

        while (!(chunk = await reader.read()).done) {
            const decodedChunk = decoder.decode(chunk.value);
            fullResponse += decodedChunk; // Append the chunk to the full response

            const messages = decodedChunk
                .split("\n")
                .filter((line) => line);
            messages.forEach((msg) => {
                try {
                    processResponse(msg);
                } catch (error) {
                    console.error("Error parsing message:", msg, error);
                }
            });
        }

        uploadedFiles = [
            ...uploadedFiles,
            ...Array.from(files).map((file) => file.name),
        ];
        displayUploadedFiles();

        document.getElementById("upload-files").value = ""; // Clear the file input
        
        // Re-enable inputs after response is complete
        enableInputs();
        isWaitingForResponse = false;
    } catch (error) {
        console.error("Error sending message:", error);
        alert("Error sending message: " + error);
        enableInputs();
        isWaitingForResponse = false;
    }
}

function handleKeyDown(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

// Function to handle income statement responses
function handleIncomeStatementResponse(response) {
    const chatBox = document.getElementById('chat-box');
    
    // Create a message container
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    
    // Add the main response text
    const textPara = document.createElement('p');
    textPara.textContent = response.text;
    messageDiv.appendChild(textPara);
    
    // If there's a statement, add it in a pre-formatted code block
    if (response.statement) {
        const statementPre = document.createElement('pre');
        statementPre.className = 'income-statement';
        statementPre.textContent = response.statement;
        messageDiv.appendChild(statementPre);
    }
    
    // If there's an Excel file, add a download link
    if (response.excel_path) {
        const downloadLink = document.createElement('a');
        downloadLink.href = `/download?path=${encodeURIComponent(response.excel_path)}`;
        downloadLink.className = 'download-button';
        downloadLink.textContent = 'Download Excel Report';
        downloadLink.download = 'income_statement.xlsx';
        messageDiv.appendChild(downloadLink);
    }
    
    // Add to chat box
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Modify your existing processResponse function to handle different response types
function processResponse(data) {
    try {
        const response = JSON.parse(data);
        
        // Handle different response types
        if (response.type === 'income_statement') {
            handleIncomeStatementResponse(response);
        } else if (response.type === 'error') {
            // Handle error response
            const chatBox = document.getElementById('chat-box');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message error-message';
            messageDiv.textContent = response.message || response.error || "An error occurred";
            chatBox.appendChild(messageDiv);
        } else {
            // Handle regular text response - use message field instead of text
            const chatBox = document.getElementById('chat-box');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message bot-message';
            messageDiv.textContent = response.message || "No response content";
            
            // Update conversation ID if provided
            if (response.conversation_id) {
                conversationId = response.conversation_id;
            }
            
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    } catch (error) {
        console.error("Error processing response:", error);
    }
}