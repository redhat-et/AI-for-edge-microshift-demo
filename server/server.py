#!/usr/bin/python3
from flask import Flask
from flask import request

import logging
import io
import requests
import cv2
import numpy as np
import threading

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

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


def streamer(camIP, camToken):
    app.logger.info("starting streamer thread")
    
    face_cascade = cv2.cuda_CascadeClassifier.create('./haarcascade_frontalface_default.xml')

    mr = MjpegReader("http://" + camIP + "/stream?token="+camToken)
    for content in mr.iter_content():
        img = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        app.logger.info("received img")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cuFrame = cv2.cuda_GpuMat(gray_img)
        faces = face_cascade.detectMultiScale(cuFrame).download()
        for (x, y, w, h) in faces:
            app.logger.info("found face at %d, %d (%d x %d)",x,y,w,h)

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

