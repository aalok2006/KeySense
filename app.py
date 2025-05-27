from flask import Flask, render_template, Response, request, jsonify
import cv2
from cvzone.HandTrackingModule import HandDetector
import numpy as np
import base64 # For sending images as text

app = Flask(__name__)

# --- Configuration --- (can be adjusted)
DETECTION_CONFIDENCE = 0.8
CLICK_DISTANCE_THRESHOLD = 35

# --- Keyboard Layout (same as local) ---
keys = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"],
    ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "<-"]
]

# --- Button Class (Simplified for server-side logic if needed, or just use positions) ---
class Button():
    def __init__(self, pos, text, size=[85, 85]): # Keep consistent with client
        self.pos = pos
        self.size = size
        self.text = text

    def is_over(self, point, frame_width, frame_height, display_width, display_height):
        # Adjust point coordinates based on scaling between actual frame and display size
        # This is crucial if the video displayed in browser is scaled
        scale_x = frame_width / display_width
        scale_y = frame_height / display_height
        
        # Assuming button positions are relative to the display_width/height
        # For simplicity here, let's assume positions are relative to original frame
        # A more robust solution would pass display dimensions from client
        # or define button positions relative to a fixed coordinate system
        
        btn_x, btn_y = self.pos
        btn_w, btn_h = self.size

        # Example: If button positions are based on a 1280x720 canvas displayed on client
        # And processing frame is, say, 640x480, coordinates need scaling
        # For now, assuming point is already scaled to server's processing frame
        
        return btn_x < point[0] < btn_x + btn_w and \
               btn_y < point[1] < btn_y + btn_h


buttonList = []
for i in range(len(keys)):
    for j, key_char in enumerate(keys[i]):
        x_pos = 100 * j + 50 # These positions need to match the client-side canvas
        y_pos = 100 * i + 50
        if key_char == "<-":
            buttonList.append(Button([x_pos, y_pos], key_char, size=[120, 85]))
        else:
            buttonList.append(Button([x_pos, y_pos], key_char))

detector = HandDetector(detectionCon=DETECTION_CONFIDENCE, maxHands=1)

@app.route('/')
def index():
    return render_template('index.html')

def image_from_b64(b64_string):
    """Decodes a base64 string to an OpenCV image."""
    if "," in b64_string: # Handle 'data:image/jpeg;base64,' prefix
        b64_string = b64_string.split(',')[1]
    img_bytes = base64.b64decode(b64_string)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

@app.route('/process_frame', methods=['POST'])
def process_frame():
    data = request.get_json()
    if not data or 'image_data' not in data:
        return jsonify({"error": "No image data"}), 400

    try:
        img = image_from_b64(data['image_data'])
        if img is None:
            return jsonify({"error": "Could not decode image"}), 400

        # --- Perform hand detection and logic ---
        img_for_detection = cv2.flip(img, 1) # Flip for mirror view, assuming client sends direct feed
        hands, _ = detector.findHands(img_for_detection, flipType=False) # Already flipped

        pressed_key = None
        landmarks_for_client = [] # To draw hand on client

        if hands:
            hand = hands[0]
            lmList = hand['lmList']
            landmarks_for_client = [{'x': lm[0], 'y': lm[1]} for lm in lmList] # Send scaled landmarks

            index_finger_tip = lmList[8][:2]
            middle_finger_tip = lmList[12][:2]

            # Important: Button positions (x_pos, y_pos) must match what's drawn on client canvas
            # And lmList coordinates must be relative to the same coordinate system.
            # The client should send its canvas dimensions if they differ from video dimensions.
            # For now, assuming client canvas is 1280x720 and video is also processed at that size or scaled.

            for button in buttonList:
                # We need to ensure the coordinates match. The lmList coordinates are for the img_for_detection.
                # If the client draws buttons on a canvas of a different size than the video it sends,
                # or if the server resizes the image, scaling is needed.
                # Let's assume the client sends a 640x480 frame, and buttons are defined for this.
                # If button.pos is defined for a 1280x720 layout, it needs scaling.
                # For simplicity, let's assume client sends frame and buttons are on that frame's scale.
                
                # To make this more robust, the client should send its drawing canvas dimensions
                # and the server should scale lmList coordinates to match that canvas.
                # Or, buttons are defined for the server's processing resolution.
                
                # Let's assume button positions are defined based on a 1280x720 space,
                # and img_for_detection is also that size.
                # If client sends smaller frames, server could resize or client needs to scale landmarks.

                # For this example: assume index_finger_tip is in the coordinate system of img_for_detection
                # and button.pos is relative to a fixed layout (e.g., 1280x720).
                # If img_for_detection is not 1280x720, landmarks need to be scaled.
                # Let's assume img_for_detection IS the size for which buttons are defined.
                
                if button.is_over(index_finger_tip, img_for_detection.shape[1], img_for_detection.shape[0], 
                                  img_for_detection.shape[1], img_for_detection.shape[0]): # Assuming display = frame
                    length, _, _ = detector.findDistance(index_finger_tip, middle_finger_tip, img_for_detection, draw=False)
                    if length < CLICK_DISTANCE_THRESHOLD:
                        pressed_key = button.text
                        break # Process one click at a time

        return jsonify({
            "pressed_key": pressed_key,
            "landmarks": landmarks_for_client, # Send landmarks to draw on client
            "img_shape": {"width": img_for_detection.shape[1], "height": img_for_detection.shape[0]}
        })

    except Exception as e:
        print(f"Error processing frame: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) # For local testing
