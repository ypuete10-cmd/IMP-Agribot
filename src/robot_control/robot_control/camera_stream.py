#!/usr/bin/env python3
import cv2
from flask import Flask, Response

app = Flask(__name__)

# USB webcam
camera = cv2.VideoCapture(0)

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return """<html><head><title>Robot Camera</title></head>
    <body><h1>Live Camera Feed</h1>
    <img src="/video_feed" width="640" height="480"></body></html>"""

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def main(args=None):
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
