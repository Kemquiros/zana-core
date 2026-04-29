# ZANA on Windows — Installation Guide (WSL 2)

> Full step-by-step guide for Windows users. Estimated time: 15–20 minutes.

## Requirements

- Windows 10 version 2004+ or Windows 11
- 8 GB RAM minimum (16 GB recommended)
- 20 GB free disk space

---

## Step 1 — Install WSL 2

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This installs WSL 2 and Ubuntu automatically. Restart when prompted.

> Already have WSL? Make sure you're on version 2:
> ```powershell
> wsl --set-default-version 2
> wsl --update
> ```

---

## Step 2 — Create your Ubuntu user

After rebooting, Ubuntu opens and asks you to create a username and password. This password is used for `sudo` commands — choose something you'll remember.

Verify the environment:

```bash
uname -r           # shows something like 5.15.x or 6.x
python3 --version  # must be 3.10+ (Ubuntu 22.04 ships 3.10, 24.04 ships 3.12)
```

---

## Step 3 — Install Docker Desktop

1. Download **Docker Desktop** from [docs.docker.com/get-docker](https://docs.docker.com/get-docker/)
2. During installation, check **"Use WSL 2 based engine"**
3. After launch: Docker Desktop → **Settings → Resources → WSL Integration** → enable your Ubuntu distribution

Verify from inside Ubuntu:

```bash
docker --version
docker info
```

Both must respond without errors.

---

## Step 4 — Prepare your Obsidian Vault

ZANA writes memories into an Obsidian vault. Because Obsidian runs on Windows (not inside WSL), the folder must live on the Windows filesystem — not under `/home/your_user`.

Create the folder from PowerShell:

```powershell
mkdir "$env:USERPROFILE\Documents\ZANA_Vault"
```

From WSL this folder is visible as:

```
/mnt/c/Users/YourWindowsName/Documents/ZANA_Vault
```

> If you already have an Obsidian vault, note its Windows path — you'll use it in Step 7.

---

## Step 5 — Install Python 3.12 (Ubuntu 22.04 only)

Skip this step if you're on Ubuntu 24.04+ (already ships Python 3.12).

```bash
sudo apt update && sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install -y python3.12 python3.12-venv python3.12-distutils
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
python3 --version  # must show Python 3.12.x
```

---

## Step 6 — Run the ZANA installer

Use this exact syntax — **not** `curl | bash`:

```bash
bash <(curl -LsSf https://zana.vecanova.com/install.sh)
```

> **Why `bash <(...)` and not `curl | bash`?**
>
> `curl | bash` pipes stdin directly into bash, destroying the terminal (TTY). This causes interactive prompts to abort immediately. `bash <(...)` runs the script in a subprocess that keeps TTY access intact.

The installer:
- Checks dependencies (Python, Git, Docker, uv)
- Clones the repository to `~/.zana/core-repo`
- Installs the `zana` CLI via `uv tool install`
- Adds `zana` to your `PATH` in `~/.bashrc`

---

## Step 7 — Complete interactive setup

After installation, `zana start` launches the first-run wizard:

```
Configuración de Bóveda Soberana
? Ruta a tu bóveda de Obsidian (donde ZANA leerá/escribirá):
```

Type your vault path (Tab autocompletes):

```
/mnt/c/Users/YourWindowsName/Documents/ZANA_Vault
```

Then it asks for API keys (press Enter to skip any):

```
  Anthropic API key (Recommended for Analyst): sk-ant-...
  OpenAI API key: [Enter to skip]
  Gemini API key: [Enter to skip]
  Groq API key:   [Enter to skip]
```

Keys are saved to `~/.zana/.env` — you can edit them later with `nano ~/.zana/.env`.

---

## Step 8 — Verify services are running

```bash
zana status
```

All services should be green:

```
● postgres     running   port 55433
● redis        running   port 56380
● neo4j        running   port 57474
● gateway      running   port 54446
● aria-ui      running   port 54448
```

Open the web panel in your Windows browser:

```
http://localhost:54448
```

---

## Essential commands

```bash
zana start          # Start all services
zana stop           # Stop all services
zana status         # Real-time service health
zana chat           # Open chat REPL with your Aeon
zana aeon list      # Show your agent fleet
zana setup          # Re-run the configuration wizard
```

---

## Troubleshooting

**`docker: command not found`**

Docker Desktop is installed but WSL integration is not enabled. Go to Docker Desktop → Settings → Resources → WSL Integration → enable Ubuntu.

**`permission denied` when starting services**

```bash
sudo usermod -aG docker $USER
# Close and reopen the WSL terminal
```

**Web panel doesn't load at `http://localhost:54448`**

```bash
zana status
zana stop && zana start
```

**Obsidian doesn't see the vault after install**

The vault must be at `C:\Users\YourName\Documents\ZANA_Vault` (Windows path). Open Obsidian → Open folder as vault → navigate to that folder.

**Need to change the vault path**

```bash
zana setup
# or edit directly:
nano ~/.zana/.env   # update VAULT_PATH=/mnt/c/Users/.../YourVault
```

---

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*
