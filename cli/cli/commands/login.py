import json
import time
import webbrowser
from pathlib import Path

import httpx
import typer

from cli.tui.theme import console

CREDENTIALS_FILE = Path.home() / ".config" / "zana" / "credentials.json"
# Device flow endpoint — replace with real auth server when available
DEVICE_AUTH_URL = "https://auth.zana.ai/oauth/device/code"
TOKEN_URL = "https://auth.zana.ai/oauth/token"
CLIENT_ID = "zana-cli"


def _save_credentials(token: str) -> None:
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps({"access_token": token}, indent=2))
    CREDENTIALS_FILE.chmod(0o600)


def _load_credentials() -> dict | None:
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        return json.loads(CREDENTIALS_FILE.read_text())
    except Exception:
        return None


def cmd_login() -> None:
    creds = _load_credentials()
    if creds:
        console.print("[success]Already authenticated.[/success]")
        console.print("[muted]Run `zana login --reauth` to get a new token.[/muted]")
        return

    console.print("[primary]Initiating device authorization flow...[/primary]")

    try:
        r = httpx.post(DEVICE_AUTH_URL, data={"client_id": CLIENT_ID}, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        # Offline fallback: prompt for API key directly
        console.print("[warning]Auth server unreachable. Enter API key directly.[/warning]")
        key = typer.prompt("ANTHROPIC_API_KEY", hide_input=True)
        _save_credentials(key)
        console.print("[success]API key stored at ~/.config/zana/credentials.json[/success]")
        return

    device_code = data["device_code"]
    user_code = data["user_code"]
    verification_uri = data["verification_uri"]
    interval = data.get("interval", 5)
    expires_in = data.get("expires_in", 300)

    console.print(f"\n  Open [code]{verification_uri}[/code]")
    console.print(f"  Enter code: [accent]{user_code}[/accent]\n")

    try:
        webbrowser.open(verification_uri)
    except Exception:
        pass

    deadline = time.time() + expires_in
    console.print("[muted]Waiting for authorization...[/muted]", end="")

    while time.time() < deadline:
        time.sleep(interval)
        try:
            tr = httpx.post(TOKEN_URL, data={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }, timeout=10)

            if tr.status_code == 200:
                token_data = tr.json()
                _save_credentials(token_data["access_token"])
                console.print()
                console.print("[success]Authenticated.[/success]")
                return

            err = tr.json().get("error", "")
            if err == "authorization_pending":
                console.print("[muted].[/muted]", end="")
                continue
            if err == "slow_down":
                interval += 5
                continue
            console.print(f"\n[error]Auth failed: {err}[/error]")
            raise typer.Exit(1)

        except httpx.RequestError:
            console.print("[muted].[/muted]", end="")

    console.print("\n[error]Authorization timed out.[/error]")
    raise typer.Exit(1)


def cmd_logout() -> None:
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        console.print("[success]Credentials removed.[/success]")
    else:
        console.print("[muted]No credentials found.[/muted]")
