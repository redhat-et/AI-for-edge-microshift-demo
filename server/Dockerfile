FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3
RUN pip3 install flask face_recognition
WORKDIR /app
COPY server.py /app
COPY haarcascade_frontalface_default.xml /app
ENV FLASK_APP=server
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
CMD python3 -m flask run --host 0.0.0.0
