# ZANA Installation Guide: Linux (Ubuntu)

This guide covers the prerequisites and steps to install ZANA on a native Linux environment (Ubuntu 22.04 LTS or newer recommended).

## 1. Prerequisites

Before running the ZANA installer, you must ensure that **Docker** and **Python 3.12+** are available on your system.

### Install Docker Engine
1. Update your apt package index and install packages to allow apt to use a repository over HTTPS:
   ```bash
   sudo apt-get update
   sudo apt-get install ca-certificates curl gnupg
   ```
2. Add Docker's official GPG key:
   ```bash
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg
   ```
3. Set up the repository:
   ```bash
   echo \
     "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```
4. Install Docker Engine and Docker Compose:
   ```bash
   sudo apt-get update
   sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```
5. Manage Docker as a non-root user:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

### Install Python 3.12
Ubuntu 22.04 defaults to Python 3.10. You can install Python 3.12 via the Deadsnakes PPA:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

## 2. Install ZANA

Run the official installation script:
```bash
bash <(curl -LsSf https://zana.vecanova.com/install.sh)
```
The script will download the necessary containers and initialize the virtual environments.

## 3. Next Steps
Once installed, start the system:
```bash
zana start
```
Then navigate to `http://localhost:54448` to access Aria UI and complete the Sovereign Login setup.
