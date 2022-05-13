#!/bin/sh

podman build . -f Dockerfile.rpi4 -t docker.io/mangelajo/cam-server:latest-nogpu
podman push docker.io/mangelajo/cam-server:latest-nogpu
oc delete pod -l app=camserver --grace-period=1 --wait=false
while true; do
   sleep 5
   oc logs -f -l app=camserver
done
