FROM ubuntu:22.04

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    iproute2 \
    iputils-ping \
    net-tools \
    iperf \
    iperf3 \
    python3 \
    python3-pip \
    curl \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip3 install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Start OpenvSwitch in the background by default (needed for Mininet)
# and keep the container running
CMD service openvswitch-switch start && /bin/bash
