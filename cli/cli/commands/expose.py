import os
import sys
import stat
import platform
import urllib.request
import subprocess
import re
import time
from pathlib import Path
from cli.tui.theme import console

ZANA_CONFIG_DIR = Path.home() / ".config" / "zana"
BIN_DIR = ZANA_CONFIG_DIR / "bin"
CLOUDFLARED_PATH = BIN_DIR / "cloudflared"

def get_cloudflared_url():
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    base_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    
    if system == "linux":
        if machine in ["x86_64", "amd64"]:
            return base_url + "cloudflared-linux-amd64"
        elif machine in ["aarch64", "arm64"]:
            return base_url + "cloudflared-linux-arm64"
    elif system == "darwin":
        if machine in ["x86_64", "amd64"]:
            return base_url + "cloudflared-darwin-amd64.tgz" # Actually darwin binary is inside tgz, let's use homebrew suggestion or direct binary if available.
            # Cloudflared provides 'cloudflared-darwin-amd64.tgz', but let's just use brew for macOS if possible or download the tgz and extract.
            # Better yet, for simplicity in this script, we can just say darwin is supported via brew.
    return None

def install_cloudflared():
    if CLOUDFLARED_PATH.exists():
        return True

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    
    system = platform.system().lower()
    if system == "darwin":
        console.print("[muted]On macOS, please install cloudflared via Homebrew: brew install cloudflare/cloudflare/cloudflared[/muted]")
        return False
        
    url = get_cloudflared_url()
    if not url:
        console.print(f"[error]Unsupported OS or architecture for automatic cloudflared installation.[/error]")
        return False

    with console.status("[primary]Downloading cloudflared...[/primary]"):
        try:
            urllib.request.urlretrieve(url, CLOUDFLARED_PATH)
            st = os.stat(CLOUDFLARED_PATH)
            os.chmod(CLOUDFLARED_PATH, st.st_mode | stat.S_IEXEC)
            return True
        except Exception as e:
            console.print(f"[error]Failed to download cloudflared: {e}[/error]")
            return False

def cmd_expose(port: int = 54448):
    console.print(f"\n[primary]ZANA Sovereign Bridge[/primary] [muted]v2.9[/muted]")
    
    system = platform.system().lower()
    cf_bin = str(CLOUDFLARED_PATH)
    
    if system == "darwin":
        import shutil
        if shutil.which("cloudflared"):
            cf_bin = "cloudflared"
        else:
            console.print("[warning]cloudflared is not installed. Run: brew install cloudflare/cloudflare/cloudflared[/warning]")
            return
    else:
        if not install_cloudflared():
            return

    console.print(f"[muted]Forging secure tunnel to Aria UI (port {port})...[/muted]")
    
    # Run cloudflared
    try:
        process = subprocess.Popen(
            [cf_bin, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Cloudflared outputs the URL to stderr
        url = None
        for i in range(20):
            line = process.stderr.readline()
            if "trycloudflare.com" in line:
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if match:
                    url = match.group(0)
                    break
            time.sleep(0.5)
            
        if url:
            console.print(f"\n[success]Sovereign Bridge Established![/success]")
            console.print(f"[accent]Remote Access URL:[/accent] [bold white]{url}[/bold white]\n")
            console.print("[muted]Press Ctrl+C to collapse the bridge and revoke access.[/muted]")
            
            try:
                process.wait()
            except KeyboardInterrupt:
                console.print("\n[warning]Collapsing the bridge...[/warning]")
                process.terminate()
        else:
            console.print("[error]Failed to establish the bridge. Check if cloudflared is running correctly.[/error]")
            process.terminate()
            
    except Exception as e:
        console.print(f"[error]Error starting tunnel: {e}[/error]")
