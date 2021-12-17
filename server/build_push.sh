#!/bin/sh

docker build . -t quay.io/mangelajo/cam-server:latest
docker push quay.io/mangelajo/cam-server:latest

