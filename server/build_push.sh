#!/bin/sh

docker build . -t docker.io/mangelajo/cam-server:latest
docker push docker.io/mangelajo/cam-server:latest
oc delete pod -l app=camserver --grace-period=1 --wait=false
while true; do
   sleep 5
   oc logs -f -l app=camserver
done
