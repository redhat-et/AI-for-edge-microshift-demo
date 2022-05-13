#!/bin/sh
podman build . -f Dockerfile.rpi4 -t quay.io/mangelajo/microshift-ap-cams:latest-rpi4
podman push quay.io/mangelajo/microshift-ap-cams:latest-rpi4

