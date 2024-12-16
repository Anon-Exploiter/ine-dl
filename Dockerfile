# Use the official Ubuntu image from the Docker Hub
FROM ubuntu:latest

WORKDIR /app

# Update the package lists and install Python3, pip, and git
RUN apt-get update && \
    apt-get install -y git aria2 python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Clone the repository and install the required Python packages
RUN git clone https://github.com/Anon-Exploiter/ine-dl --depth 1 && \
    cd ine-dl && \
    pip3 install -r requirements.txt --break-system-packages

# Keep the container running
CMD ["tail", "-f", "/dev/null"]