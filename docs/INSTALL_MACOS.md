# ZANA Installation Guide: macOS

This guide covers the prerequisites and steps to install ZANA on macOS (Apple Silicon M1/M2/M3 or Intel).

## 1. Prerequisites

Before running the ZANA installer, you must ensure that **Docker Desktop** and **Python 3.12+** are available on your system.

### Install Docker Desktop
1. Download Docker Desktop for Mac from the [official Docker website](https://docs.docker.com/desktop/install/mac-install/).
2. Open the downloaded `.dmg` file and drag Docker to your Applications folder.
3. Open Docker from your Applications folder to complete the installation and ensure the Docker daemon is running (look for the whale icon in your menu bar).
4. Verify the installation in your terminal:
   ```bash
   docker --version
   docker compose version
   ```

### Install Python 3.12 (via Homebrew)
If you do not have Homebrew installed, install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install Python 3.12:
```bash
brew install python@3.12
```

## 2. Install ZANA

### Option A — Official Installer (Recommended)
With Python 3.12 ready, execute the official installation script:
```bash
curl -LsSf https://zana.vecanova.com/install.sh | bash
```
The script will check dependencies and install the ZANA CLI via `uv tool`.

### Option B — pipx (Python)
```bash
brew install pipx
pipx ensurepath
pipx install vecanova-zana
zana init
```

### Option C — npm (Node)
```bash
npm install -g @vecanova/zana
zana init
```

## 3. Next Steps
ZANA v3.1.0 is **zero-friction**: you don't need Docker to start chatting.
```bash
zana init   # create your Aeon
zana chat   # start talking
```
If you want the full visual experience and graph memory, then run:
```bash
zana start  # boots the Docker stack
```
Then navigate to `http://localhost:54448` to access Aria UI.
