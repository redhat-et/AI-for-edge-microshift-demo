import cv2
import face_recognition
import numpy as np


# TODO, traverse directories and generate automatically
ricky1_face_encoding = face_recognition.face_encodings(
    face_recognition.load_image_file("faces/Ricardo Noriega/ricky1.jpg"))[0]

ajo1_face_encoding = face_recognition.face_encodings(
    face_recognition.load_image_file("faces/Miguel Angel Ajo/ajo1.jpg"))[0]

known_face_encodings = [
        ricky1_face_encoding,
        ajo1_face_encoding,
        ]

known_face_names = [
        "Ricardo Noriega",
        "Miguel Angel Ajo"
    ]

RATIO = 0.25


def find_and_mark_faces(frame, logger, cam_ip):
    small_frame = cv2.resize(frame, (0, 0), fx=RATIO, fy=RATIO)
    face_locations = face_recognition.face_locations(small_frame, 1, "hog")
    names = []
    face_encodings = face_recognition.face_encodings(small_frame, face_locations)
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
        names.append(name)

        logger.info("[cam %s] face_locations = %s, names = %s", cam_ip, face_locations, names)

        for (top, right, bottom, left), name in zip(face_locations, names):
            add_name_box(frame, left, top, bottom, right, name)

    return frame


def add_name_box(frame, left, top, bottom, right, name):
    inv_ratio = 1.0 / RATIO
    top = int(top * inv_ratio)
    right = int(right * inv_ratio)
    bottom = int(bottom * inv_ratio)
    left = int(left * inv_ratio)
    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
