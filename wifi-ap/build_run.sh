#!/bin/sh
docker build . -t quay.io/mangelajo/microshift-ap-cams:latest
docker run -ti --rm --privileged --net=host --name wifiap quay.io/mangelajo/microshift-ap-cams:latest

