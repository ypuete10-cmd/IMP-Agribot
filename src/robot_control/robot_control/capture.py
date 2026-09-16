#!/usr/bin/env python3
import cv2
import sys
import time

def capture_image(filename="plant_photo.jpg", device=0):
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return False

    # Let camera adjust exposure
    time.sleep(2)

    ret, frame = cap.read()
    cap.release()

    if ret and frame is not None:
        cv2.imwrite(filename, frame)
        print(f"Saved: {filename} ({frame.shape[1]}x{frame.shape[0]})")
        return True
    else:
        print("Error: Failed to capture frame")
        return False

def main(args=None):
    name = sys.argv[1] if len(sys.argv) > 1 else "plant_photo.jpg"
    capture_image(name)

if __name__ == '__main__':
    main()
