#!/usr/bin/python3
from flask import Flask
from flask import request
from flask import Response
import logging
import threading
import time

from faces import *
from mjpeg_streamer import MjpegReader

# frame to be shared via mjpeg server out
outputFrames = {}
lock = threading.Lock()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/register")
def register():
    if "token" not in request.args or "ip" not in request.args:
        return "Invalid registration, you need both token and ip", 400

    cam_ip = request.args["ip"]
    cam_token = request.args["token"]
    
    app.logger.info("camera @%s registered with token %s", cam_ip, cam_token)
    threading.Thread(target=streamer_thread, name=None, args=[cam_ip, cam_token]).start()

    return "ACK", 200


def streamer_thread(cam_ip, cam_token):

    app.logger.info("starting streamer thread for cam %s", cam_ip)
    
    mr = MjpegReader("http://" + cam_ip + "/stream?token=" + cam_token)
    for content in mr.iter_content():
        frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        process_streamer_frame(cam_ip, frame)


def process_streamer_frame(cam_ip, frame):
    global outputFrames, lock
    frame_out = find_and_mark_faces(frame, app.logger, cam_ip)
    with lock:
        outputFrames[cam_ip] = frame_out.copy()


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate_video_feed(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


def generate_video_feed():
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
            
            all_cams = cv2.hconcat(frames)

            (flag, encodedImage) = cv2.imencode(".jpg", all_cams)

            # ensure the frame was successfully encoded
            if not flag:
                continue
            # yield the output frame in the byte format
            yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n'
        
        time.sleep(0.1)
