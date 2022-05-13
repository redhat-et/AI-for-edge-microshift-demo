# AI-for-edge-microshift-demo
This repository contains the code developed for the talk "AI at the Edge with MicroShift" developed by Miguel Angel Ajo and Ricardo Noriega.

You can find the video of our presentation [here](https://www.youtube.com/watch?v=kR9eSxM9qgg).

The end goal of this demo is to run a face detection and face recognition AI model in a cloud-native fashion using MicroShift in an edge computing scenario. In order to do this, we used the [NVIDIA Jetson](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/) family boards (tested on Jetson TX2 and Jetson Xavier NX).

This demo repository is structured into three different folders:

* esp32cam: software used to program the ESP32 cameras.
* wifi-ap: script running inside a Kubernetes pod that creates a WIFI SSID.
* server: Flask server that receives video streams from the cameras and performs face detection and recognition.


## ESP32 Cameras Software

The code has been built using [PlatformIO](https://platformio.org/) with the Arduino framework. VSCode IDE has a very convenient plugin that allows you to choose the platform to use, compile the code and push it to the device from one place.

There are tons of tutorials on how to use an ESP32 Camera with Platform IO, but one of the most relevant files to look at is the platformio.ini located in the esp32cam directory:

```
[env:esp32cam]
#upload_speed = 460800
upload_speed = 921600
platform = espressif32
board = esp32cam
framework = arduino
lib_deps = yoursunny/esp32cam@0.0.20210226
monitor_port=/dev/ttyUSB0
monitor_speed=115200
monitor_rst=1
monitor_dtr=0
```

Once you connect the camera to your laptop, a new `/dev/ttyUSB0` will appear, and this file determines what platform the code must be compiled for.

If you want the cameras to connect to a different SSID, please modify the following file `esp32cam/src/wifi_pass.h`:

```
const char* WIFI_SSID = "camwifi";
const char* WIFI_PASS = "thisisacamwifi";
```

## Running MicroShift (jetson L4T)

At this point, we have programmed our ESP32 cameras. We assume that you have installed the standard L4T operating system specific to your Jetson board, and it is ready to install some packages (as root).

```
apt install -y curl jq runc iptables conntrack nvidia-container-runtime nvidia-container-toolkit
```

Disable firewalld:

```
systemctl disable --now firewalld
```

Install CRI-O as our container runtime:

```
curl https://raw.githubusercontent.com/cri-o/cri-o/main/scripts/get | bash 

```

Configure CRI-O in order to use the NVIDIA Container Runtime


```
rm /etc/crio/crio.conf.d/*

cat << EOF > /etc/crio/crio.conf.d/10-nvidia-runtime.conf
[crio.runtime]
default_runtime = "nvidia"

[crio.runtime.runtimes.nvidia]
runtime_path = "/usr/bin/nvidia-container-runtime"
EOF

cat << EOF > /etc/crio/crio.conf.d/01-crio-runc.conf
[crio.runtime.runtimes.runc]
runtime_path = "/usr/sbin/runc"
runtime_type = "oci"
runtime_root = "/run/runc"
EOF

rm -rf /etc/cni/net.d/10-crio-bridge.conf
```

Download MicroShift binary:

```
export ARCH=arm64
export VERSION=$(curl -s https://api.github.com/repos/redhat-et/microshift/releases | grep tag_name | head -n 1 | cut -d '"' -f 4)
curl -LO https://github.com/redhat-et/microshift/releases/download/$VERSION/microshift-linux-${ARCH}
mv microshift-linux-${ARCH} /usr/bin/microshift; chmod 755 /usr/bin/microshift
```
Create the MicroShift's systemd service:

```
cat << EOF > /usr/lib/systemd/system/microshift.service
[Unit]
Description=MicroShift
After=crio.service

[Service]
WorkingDirectory=/usr/bin/
ExecStart=/usr/bin/microshift run
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
```

Enable and run CRI-O and MicroShift services:
```
systemctl enable crio --now
systemctl enable microshift.service --now
```
Download and install the oc client:

```
curl -LO https://mirror.openshift.com/pub/openshift-v4/arm64/clients/ocp/stable/openshift-client-linux.tar.gz
tar xvf openshift-client-linux.tar.gz
chmod +x oc
mv oc /usr/local/bin
```

Set Kubeconfig environment variable:

```
export KUBECONFIG=/var/lib/microshift/resources/kubeadmin/kubeconfig
```

If MicroShift is up and running, after a couple of minutes you should see the following pods:

```
root@jetson-nx:~# oc get pod -A
NAMESPACE                       NAME                                  READY   STATUS    RESTARTS   AGE
kube-system                     kube-flannel-ds-7rz4d                 1/1     Running   0          17h
kubevirt-hostpath-provisioner   kubevirt-hostpath-provisioner-9m9mc   1/1     Running   0          17h
openshift-dns                   dns-default-6pbkt                     2/2     Running   0          17h
openshift-dns                   node-resolver-g4d8g                   1/1     Running   0          17h
openshift-ingress               router-default-85bcfdd948-tsk29       1/1     Running   0          17h
openshift-service-ca            service-ca-7764c85869-dvdtm           1/1     Running   0          17h

```

Now, we have our cloud-native platform ready to run workloads. Think about this: we have an edge computing optimized Kubernetes distribution ready to run an AI workload, and make use of the integrated GPU from the NVIDIA Jetson board. It's awesome!

## Wi-FI Access Point

We don't want to depend on any available wireless network that we don't control and might not be secured. Furthermore, in order to allow users to test this demo, it has to be self-contained. This is why we have created a pod that creates a Wi-Fi Access Point with the credentials mentioned in the above section.

```
SSID: camwifi
Password: thisisacamwifi
```

If you want to expose a different SSID and use a different password, please change the file `wifi-ap/hostapd.conf`.

Now, let's deploy this pod on MicroShift.

```
oc apply -f wifi-ap/cam-ap.yaml
```

After a few seconds, we should be able to see it running:

```
oc get pods

NAME                         READY   STATUS    RESTARTS   AGE
cameras-ap-b6b6c9c96-krm45   1/1     Running   0          3s
```

Looking at the logs of the pod, you will see how the process inside will provide IP addresses to the cameras or any device connected to the wireless network.


## AI models

The final step is to deploy the AI models that will perform face detection and face recognition. This pod is basically a Flask server that will get the streams of the cameras once they are connected, and start working on a discrete number of frames.

Let's deploy the AI models on MicroShift:

```
oc apply -f server/cam-server.yaml
```

After few seconds:

```
oc get pods

NAME                         READY   STATUS    RESTARTS   AGE
cameras-ap-b6b6c9c96-krm45   1/1     Running   0          4m37s
camserver-cc996fd86-pkm45    1/1     Running   0          42s
```

We also need to create a service and expose a route for this pod:

```
oc expose deployment camserver
oc expose service camserver --hostname microshift-cam-reg.local
```

MicroShift has mDNS built-in capabilities, and this route will be automatically announced, so the cameras can register to this service, and start streaming video.

Looking at the camserver logs, we can see this registration process:

```
oc logs camserver-cc996fd86-pkm45

 * Serving Flask app 'server' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on all addresses.
   WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://10.85.0.36:5000/ (Press CTRL+C to quit)
[2022-01-21 11:18:46,203] INFO in server: camera @192.168.66.89 registered with token a53ca190
[2022-01-21 11:18:46,208] INFO in server: starting streamer thread
[2022-01-21 11:19:34,674] INFO in server: starting streamer thread
10.85.0.1 - - [21/Jan/2022 11:19:34] "GET /register?ip=192.168.66.89&token=a53ca190 HTTP/1.1" 200 -
```

Finally, open a browser with the following URL:

```
http://microshift-cam-reg.local/video_feed
```

This web will show you the feeds of all the cameras that have been registered and you will be able to see how faces are detected.


## Conclusion

This demo is just a simple use case of what an edge computing scenario would look like. Running AI/ML models on top of an embedded system like the NVIDIA Jetson family, and leveraging cloud-native capabilities with MicroShift. 

We hope you enjoy it!


# Installing on Fedora 35 / aarch64 rpi4
```bash
sudo dnf module enable -y cri-o:1.21
sudo dnf copr enable -y @redhat-et/microshift
sudo dnf install -y cri-o cri-tools nss-mdns avahi microshift

hostnamectl set-hostname microshift-rpi64.local
systemctl enable --now avahi-daemon.service


firewall-cmd --zone=trusted --add-source=10.42.0.0/16 --permanent
firewall-cmd --zone=public --add-port=80/tcp --permanent
firewall-cmd --zone=public --add-port=443/tcp --permanent
# enable mdns
firewall-cmd --zone=public --add-port=5353/udp --permanent
# this one is used by the dhcp server on the acccess point
firewall-cmd --zone=public --add-service=dhcp --permanent
# this rule allows connections from the cameras into this host
firewall-cmd --zone=trusted --add-source=192.168.66.0/24 --permanent
firewall-cmd --reload

cat >/etc/NetworkManager/conf.d/99-unmanaged-devices.conf <<EOF
[keyfile]
unmanaged-devices=interface-name:wlan0
EOF

curl -L -o /etc/yum.repos.d/microshift-containers.repo \
           https://copr.fedorainfracloud.org/coprs/g/redhat-et/microshift-containers/repo/fedora-35/group_redhat-et-microshift-containers-fedora-35.repo
dnf install -y microshift-containers

systemctl enable --now avahi-daemon.service  
systemctl enable --now crio  
systemctl enable --now microshift   
```

# Installing manifests

MicroShift has a feature to auto-apply manifests from disk during startup,
you can find the documentation here https://microshift.io/docs/user-documentation/manifests/

After applying the new manifests restart MicroShift with `systemctl restart microshift`.

```bash

mkdir -p /var/lib/microshift/manifests
cd /var/lib/microshift/manifests
```

```bash
cat > kustomization.yaml <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: default
resources:
  - access-point.yaml
  - cam-server.yaml
  - service.yaml
  - mdns-route.yaml
images:
  - name: APP_IMAGE
    newName: docker.io/mangelajo/cam-server:latest-nogpu
EOF
```

```bash
cat > access-point.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cameras-ap
  labels:
    infra: ap
spec:
  replicas: 1
  selector:
    matchLabels:
      infra: ap
  template:
    metadata:
      labels:
        infra: ap
    spec:
      hostNetwork: true
      containers:
      - name: camwifi-ap
        image: quay.io/mangelajo/microshift-ap-cams:latest-rpi4
        imagePullPolicy: Always
        securityContext:
          privileged: true # otherwise hostapd can't change channels for some reason
          capabilities:
            add:
              - NET_ADMIN
              - NET_RAW
EOF
```

```bash
cat > cam-server.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: camserver
  labels:
    app: camserver
spec:
  replicas: 1
  selector:
    matchLabels:
      app: camserver
  template:
    metadata:
      labels:
        app: camserver
    spec:
      containers:
      - name: camserver
        image: APP_IMAGE
        imagePullPolicy: Always
        ports:
         - containerPort: 5000
EOF
```

```bash
cat > mdns-route.yaml <<EOF
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  labels:
    app: camserver
  name: camserver
spec:
  host: microshift-cam-reg.local
  port:
    targetPort: 5000
  to:
    kind: Service
    name: camserver
    weight: 100
  wildcardPolicy: None
EOF
```


```bash
cat > service.yaml <<EOF
apiVersion: v1
kind: Service
metadata:
  labels:
    app: camserver
  name: camserver
spec:
  ports:
  - port: 5000
    protocol: TCP
    targetPort: 5000
  selector:
    app: camserver
  sessionAffinity: None
  type: ClusterIP
EOF
```
