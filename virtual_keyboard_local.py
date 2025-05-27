import cv2
from cvzone.HandTrackingModule import HandDetector
from time import sleep, time # Added time for click debounce
import numpy as np
import cvzone
from pynput.keyboard import Controller

# --- Configuration ---
WEBCAM_ID = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
DETECTION_CONFIDENCE = 0.8
CLICK_DISTANCE_THRESHOLD = 35  # Adjusted for potentially more reliable clicks
DEBOUNCE_TIME = 0.5  # Seconds to wait after a click

# --- Keyboard Layout ---
keys = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"],
    ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "<-"] # Changed "<" to "<-" for clarity
]
# Add a space bar and potentially other keys if needed
# keys.append(["SPACE"]) # Example

finalText = ""
keyboard = Controller()

# --- Button Class ---
class Button():
    def __init__(self, pos, text, size=[85, 85]):
        self.pos = pos
        self.size = size
        self.text = text

    def draw(self, img, color=(255, 0, 255), text_color=(255, 255, 255)):
        x, y = self.pos
        w, h = self.size
        cvzone.cornerRect(img, (x, y, w, h), 20, rt=0)
        cv2.rectangle(img, self.pos, (x + w, y + h), color, cv2.FILLED)
        cv2.putText(img, self.text, (x + 20, y + 60), # Adjusted text position for better centering
                    cv2.FONT_HERSHEY_PLAIN, 3, text_color, 3) # Adjusted font size and thickness

    def is_over(self, point):
        x, y = self.pos
        w, h = self.size
        return x < point[0] < x + w and y < point[1] < y + h

# --- Initialize Buttons ---
buttonList = []
for i in range(len(keys)):
    for j, key_char in enumerate(keys[i]):
        x_pos = 100 * j + 50
        y_pos = 100 * i + 50
        # Special handling for larger keys like backspace or space
        if key_char == "<-":
            buttonList.append(Button([x_pos, y_pos], key_char, size=[120, 85]))
        # elif key_char == "SPACE":
        #     buttonList.append(Button([100 * j + 50, 100 * i + 50], " ", size=[400, 85]))
        else:
            buttonList.append(Button([x_pos, y_pos], key_char))

# --- Main Application Logic ---
def main():
    global finalText # Allow modification of finalText

    cap = cv2.VideoCapture(WEBCAM_ID)
    if not cap.isOpened():
        print(f"Error: Could not open webcam ID {WEBCAM_ID}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    detector = HandDetector(detectionCon=DETECTION_CONFIDENCE, maxHands=1) # Process one hand for simplicity

    last_click_time = 0

    while True:
        success, img = cap.read()
        if not success:
            print("Error: Failed to capture image")
            sleep(0.1)
            continue

        img = cv2.flip(img, 1) # Flip for mirror view, more intuitive

        # Find Hands
        hands, img = detector.findHands(img, flipType=False) # Already flipped the image

        # Draw all buttons
        for button in buttonList:
            button.draw(img)

        if hands:
            hand = hands[0] # Get the first detected hand
            lmList = hand['lmList'] # List of 21 landmarks

            if lmList:
                # Landmark 8 is the tip of the Index Finger
                # Landmark 12 is the tip of the Middle Finger
                index_finger_tip = lmList[8][:2] # x, y
                middle_finger_tip = lmList[12][:2]

                for button in buttonList:
                    if button.is_over(index_finger_tip):
                        # Highlight button if index finger is over it
                        button.draw(img, color=(175, 0, 175))

                        # Calculate distance between index and middle finger tips for click detection
                        length, info, img = detector.findDistance(index_finger_tip, middle_finger_tip, img)
                        # print(f"Distance: {length}") # For debugging

                        # Click detection
                        current_time = time()
                        if length < CLICK_DISTANCE_THRESHOLD and (current_time - last_click_time > DEBOUNCE_TIME):
                            button.draw(img, color=(0, 255, 0)) # Clicked color
                            key_to_press = button.text

                            if key_to_press == "<-":
                                if finalText:
                                    finalText = finalText[:-1]
                                keyboard.press('\b') # Simulate backspace
                            elif key_to_press == "SPACE": # Example for space
                                finalText += " "
                                keyboard.press(' ')
                            else:
                                finalText += key_to_press
                                keyboard.press(key_to_press)

                            last_click_time = current_time
                            sleep(0.15) # Short sleep to visually register the click color

        # Display the typed text
        cv2.rectangle(img, (50, FRAME_HEIGHT - 150), (FRAME_WIDTH - 550, FRAME_HEIGHT - 50),
                      (175, 0, 175), cv2.FILLED)
        cv2.putText(img, finalText, (60, FRAME_HEIGHT - 70),
                    cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255), 4)

        cv2.imshow("AI Virtual Keyboard - Local", img)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == 27: # ESC key
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
