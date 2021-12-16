FROM registry.fedoraproject.org/fedora-minimal:35-aarch64
RUN microdnf install -y --setopt=install_weak_deps=0 hostapd dnsmasq iproute
COPY hostapd.conf /etc/hostapd/hostapd.conf
COPY microshift-wlan0-dnsmasq-conf /etc/dnsmasq.d/

COPY run.sh /run.sh

CMD ["/run.sh"]
