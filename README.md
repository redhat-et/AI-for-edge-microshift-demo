# AI-for-edge-microshift-demo
This repository contains the code developed for the talk "AI at the Edge with MicroShift" developed by Miguel Angel Ajo and Ricardo Noriega.

# fedora 35 server setup
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

# manifests
```bash

mkdir -p /var/lib/microshift/manifests
cd /var/lib/microshift/manifests
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