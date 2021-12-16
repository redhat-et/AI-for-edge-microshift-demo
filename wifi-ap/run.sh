#!/bin/sh
set -e
set -x

WIFI=wlan0

ip a add 192.168.66.1/24 dev "${WIFI}" || true
ip l set dev "${WIFI}" up

hostapd /etc/hostapd/hostapd.conf &
dnsmasq -d
