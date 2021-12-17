#!/bin/sh
docker build . -t quay.io/mangelajo/microshift-ap-cams:latest
docker push quay.io/mangelajo/microshift-ap-cams:latest

