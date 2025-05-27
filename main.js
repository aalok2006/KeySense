const video = document.getElementById('videoElement');
const canvas = document.getElementById('overlayCanvas');
const ctx = canvas.getContext('2d');
const outputTextarea = document.getElementById('output');

const SERVER_URL = '/process_frame'; // Flask endpoint

// --- Keyboard Layout (must match server and desired display) ---
const keysLayout = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"],
    ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "<-"]
];
const buttons = [];
const BUTTON_WIDTH = 85;
const BUTTON_HEIGHT = 85;
const BUTTON_MARGIN_X = 15; // 100 (total width per button) - 85 (actual button)
const BUTTON_MARGIN_Y = 15;
const START_X = 50;
const START_Y = 50;

// Initialize button objects for drawing
keysLayout.forEach((row, i) => {
    row.forEach((keyChar, j) => {
        let x = START_X + j * (BUTTON_WIDTH + BUTTON_MARGIN_X);
        let y = START_Y + i * (BUTTON_HEIGHT + BUTTON_MARGIN_Y);
        let w = (keyChar === "<-") ? 120 : BUTTON_WIDTH; // Special width for backspace
        let h = BUTTON_HEIGHT;
        buttons.push({ x, y, w, h, text: keyChar });
    });
});


let lastProcessedKeyTime = 0;
const DEBOUNCE_INTERVAL = 500; // milliseconds, must be >= server sleep + network latency

// --- Webcam Setup ---
async function setupCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
        video.srcObject = stream;
        video.onloadedmetadata = () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            video.play();
            requestAnimationFrame(processVideoFrame);
        };
    } catch (err) {
        console.error("Error accessing webcam:", err);
        alert("Could not access webcam. Please ensure permissions are granted.");
    }
}

function drawButtons(landmarks = [], serverImgShape = null) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(255,255,255,0.7)';
    ctx.lineWidth = 2;
    ctx.font = '24px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    buttons.forEach(button => {
        ctx.fillStyle = 'rgba(255, 0, 255, 0.5)'; // Default button color
        ctx.fillRect(button.x, button.y, button.w, button.h);
        ctx.strokeRect(button.x, button.y, button.w, button.h);
        ctx.fillStyle = 'white';
        ctx.fillText(button.text, button.x + button.w / 2, button.y + button.h / 2);
    });

    // Draw landmarks if available (and scale them if necessary)
    if (landmarks.length > 0 && serverImgShape) {
        ctx.fillStyle = 'aqua';
        // Scale landmarks from server's processed image size to canvas size
        const scaleX = canvas.width / serverImgShape.width;
        const scaleY = canvas.height / serverImgShape.height;

        landmarks.forEach(lm => {
            // The server sends landmarks flipped, relative to its processing frame.
            // If client video is also flipped (common for selfie view), no more flipping needed.
            // If not, lm.x might need canvas.width - (lm.x * scaleX)
            const x = lm.x * scaleX; // Adjust if server doesn't flip for detection
            const y = lm.y * scaleY;
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, 2 * Math.PI);
            ctx.fill();
        });

        // Highlight index finger tip
        if (landmarks[8]) {
            const idxFinger = landmarks[8];
            const x = idxFinger.x * scaleX;
            const y = idxFinger.y * scaleY;
            ctx.fillStyle = 'red';
            ctx.beginPath();
            ctx.arc(x, y, 8, 0, 2 * Math.PI);
            ctx.fill();
        }
    }
}


async function processVideoFrame() {
    if (video.paused || video.ended) {
        return;
    }

    // Draw video to a temporary canvas to get image data
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
    const imageData = tempCanvas.toDataURL('image/jpeg', 0.7); // Send JPEG for smaller size

    try {
        const response = await fetch(SERVER_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: imageData })
        });

        if (!response.ok) {
            console.error("Server error:", response.status, await response.text());
            drawButtons(); // Draw buttons even if server fails
            requestAnimationFrame(processVideoFrame);
            return;
        }

        const result = await response.json();
        
        // Draw buttons and landmarks
        drawButtons(result.landmarks, result.img_shape);

        if (result.pressed_key) {
            const currentTime = Date.now();
            if (currentTime - lastProcessedKeyTime > DEBOUNCE_INTERVAL) {
                console.log("Key pressed:", result.pressed_key);
                if (result.pressed_key === "<-") {
                    outputTextarea.value = outputTextarea.value.slice(0, -1);
                } else {
                    outputTextarea.value += result.pressed_key;
                }
                lastProcessedKeyTime = currentTime;

                // Highlight pressed button briefly
                const pressedButton = buttons.find(b => b.text === result.pressed_key);
                if (pressedButton) {
                    ctx.fillStyle = 'rgba(0, 255, 0, 0.7)';
                    ctx.fillRect(pressedButton.x, pressedButton.y, pressedButton.w, pressedButton.h);
                    ctx.strokeRect(pressedButton.x, pressedButton.y, pressedButton.w, pressedButton.h);
                    ctx.fillStyle = 'white';
                    ctx.fillText(pressedButton.text, pressedButton.x + pressedButton.w / 2, pressedButton.y + pressedButton.h / 2);
                }
            }
        }

    } catch (error) {
        console.error('Error sending frame or processing response:', error);
        drawButtons(); // Still draw buttons
    }

    requestAnimationFrame(processVideoFrame);
}

// Start everything
setupCamera();
