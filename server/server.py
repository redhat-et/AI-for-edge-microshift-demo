#!/usr/bin/python3
from flask import Flask
from flask import request
from flask import Response
import logging
import io
import requests
import cv2
import numpy as np
import threading
import face_recognition
import time

# frame to be shared via mjpeg server out
outputFrames = {}
lock = threading.Lock()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)


ricky1_image = face_recognition.load_image_file("faces/ricky1.jpg")
ricky1_face_encoding = face_recognition.face_encodings(ricky1_image)[0]

ajo1_image = face_recognition.load_image_file("faces/ajo1.jpg")
ajo1_face_encoding = face_recognition.face_encodings(ajo1_image)[0]

known_face_encodings = [
        ricky1_face_encoding,
        ajo1_face_encoding,
        ]

known_face_names = [
        "Ricardo Noriega",
        "Miguel Angel Ajo"
    ]

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/register")
def register():
    if not "token" in request.args or not "ip" in request.args:
        return "Invalid registration, you need both token and ip", 400

    camIP = request.args["ip"]    
    camToken = request.args["token"]
    
    app.logger.info("camera @%s registered with token %s", camIP, camToken)
    threading.Thread(target=streamer, name=None, args=[camIP, camToken]).start()

    return "ACK", 200

RATIO = 0.25

def streamer(camIP, camToken):
    global outputFrames, lock
    app.logger.info("starting streamer thread")
    
    mr = MjpegReader("http://" + camIP + "/stream?token="+camToken)
    for content in mr.iter_content():
        frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        small_frame = cv2.resize(frame, (0, 0), fx=RATIO, fy=RATIO)
        face_locations = face_recognition.face_locations(small_frame, 1, "cnn")

        faces = []

        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        for face_encoding in face_encodings:
             matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
             name = "Unknown"
             face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
             best_match_index = np.argmin(face_distances)
             if matches[best_match_index]:
                 name = known_face_names[best_match_index]
             faces.append(name)

        app.logger.info("[cam %s] face_locations = %s, faces = %s",camIP, face_locations, faces)
            
        for (top, right, bottom, left), name in zip(face_locations, faces):
           inv_ratio = 1.0/RATIO
           top = int(top * inv_ratio)
           right = int(right * inv_ratio)
           bottom = int(bottom * inv_ratio)
           left = int(left * inv_ratio)
           cv2.rectangle(frame, (left, top), (right, bottom), (0,0,255), 2)
           cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
           font = cv2.FONT_HERSHEY_DUPLEX
           cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        with lock:
            outputFrames[camIP]= frame.copy()

@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
        mimetype = "multipart/x-mixed-replace; boundary=frame")

def generate():
    # grab global references to the output frame and lock variables
    global outputFrames, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if not outputFrames:
                time.sleep(0.01)
                continue

            # encode the frame in JPEG format
            
            frames = []
            for camIP, frame in sorted(outputFrames.items()):
                frames.append(frame)
            
            allCams = cv2.hconcat(frames)

            (flag, encodedImage) = cv2.imencode(".jpg", allCams) 
            #outputFrames = {}
            # ensure the frame was successfully encoded
            if not flag:
                continue
            # yield the output frame in the byte format
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                bytearray(encodedImage) + b'\r\n')
        
        time.sleep(0.1)

class MjpegReader():
    def __init__(self, url: str):
        self._url = url

    def iter_content(self):
        """
        Raises:
            RuntimeError
        """
        r = requests.get(self._url, stream=True)

        # parse boundary
        content_type = r.headers['content-type']
        index = content_type.rfind("boundary=")
        assert index != 1
        boundary = content_type[index+len("boundary="):] + "\r\n"
        boundary = boundary.encode('utf-8')

        rd = io.BufferedReader(r.raw)
        while True:
            length = self._parse_length(rd)
            yield rd.read(length)
            self._skip_to_boundary(rd, boundary)

    def _parse_length(self, rd) -> int:
        length = 0
        while True:
            line = rd.readline()
            if line == b'\r\n':
                return length
            if line.startswith(b"Content-Length"):
                length = int(line.decode('utf-8').split(": ")[1])
                assert length > 0


    def _skip_to_boundary(self, rd, boundary: bytes):
        for _ in range(10):
            line = rd.readline()
            if boundary in line:
                break
        else:
            raise RuntimeError("Boundary not detected:", boundary)

