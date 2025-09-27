FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Install Docker CLI
RUN apt-get update && \
    apt-get install -y docker.io docker-compose python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install pytest

# Ensure the docker group exists and add vscode user (default user in devcontainers)
RUN groupadd -f docker && \
    usermod -aG docker vscode

# Set appropriate permissions for the Docker socket (will be bind-mounted)
RUN chmod 666 /var/run/docker.sock || true
