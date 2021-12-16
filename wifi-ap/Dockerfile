FROM registry.fedoraproject.org/fedora-minimal:35-aarch64
RUN microdnf install -y hostapd dnsmasq
RUN systemctl enable hostapd && \
     systemctl enable dnsmasq && \
     systemctl disable dbus-broker && \
     systemctl disable systemd-journald && \
     systemctl disable systemd-homed && \
     systemctl disable console-getty && \
     systemctl disable systemd-logind && \
     systemctl disable systemd-oomd  && \
     systemctl disable systemd-userdbd && \
     systemctl disable systemd-resolved
COPY hostapd.conf /etc/hostapd/hostapd.conf
COPY microshift-wlan0-dnsmasq-conf /etc/dnsmasq.d/

CMD ["/sbin/init"]
