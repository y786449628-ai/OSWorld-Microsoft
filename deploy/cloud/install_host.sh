#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo bash deploy/cloud/install_host.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  git \
  curl \
  unzip \
  ca-certificates \
  python3 \
  python3-venv \
  python3-pip \
  docker.io \
  docker-compose-plugin \
  qemu-kvm \
  cpu-checker \
  libgl1 \
  libglib2.0-0 \
  libsm6 \
  libxext6 \
  libxrender1 \
  ffmpeg \
  tesseract-ocr

systemctl enable docker
systemctl restart docker

echo
echo "Host dependencies installed."
echo "KVM check:"
if command -v kvm-ok >/dev/null 2>&1; then
  kvm-ok || true
else
  egrep -c '(vmx|svm)' /proc/cpuinfo || true
fi
