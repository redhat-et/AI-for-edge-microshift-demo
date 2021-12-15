FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3
RUN apt-get install -y python3-flask
WORKDIR /app
COPY server.py /app
ENV FLASK_APP=server
CMD python3 -m flask run
