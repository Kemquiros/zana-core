import hashlib
import hmac
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC
from pathlib import Path

USER_DIR = Path.home() / ".zana" / "users"
SATELLITE_CONFIG = Path.home() / ".zana" / "satellite_config.json"
INVITES_FILE = Path.home() / ".zana" / "pending_invites.json"
ONBOARD_FILE = Path.home() / ".zana" / "pending_onboard.json"

_INVITE_TTL = 86400  # 24h


@dataclass
class UserProfile:
    platform: str
    user_id: str
    aeon_name: str
    language: str
    archetype: str
    dna_seed: str
    created_at: str
    last_seen: str

    def save(self) -> None:
        USER_DIR.mkdir(parents=True, exist_ok=True)
        path = USER_DIR / f"{self.platform}_{self.user_id}.json"
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, platform: str, user_id: str) -> "UserProfile | None":
        path = USER_DIR / f"{platform}_{user_id}.json"
        if not path.exists():
            return None
        try:
            return cls(**json.loads(path.read_text()))
        except Exception:
            return None

    def delete(self) -> bool:
        path = USER_DIR / f"{self.platform}_{self.user_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False


class UserRegistry:
    def register(
        self,
        platform: str,
        user_id: str,
        aeon_name: str,
        lang: str = "es",
        archetype: str = "unknown",
    ) -> UserProfile:
        import secrets
        from datetime import datetime

        now = datetime.now(UTC).isoformat()
        seed = secrets.token_hex(16)
        profile = UserProfile(
            platform=platform,
            user_id=str(user_id),
            aeon_name=aeon_name,
            language=lang,
            archetype=archetype,
            dna_seed=seed,
            created_at=now,
            last_seen=now,
        )
        profile.save()
        return profile

    def get(self, platform: str, user_id: str) -> UserProfile | None:
        return UserProfile.load(platform, str(user_id))

    def touch(self, platform: str, user_id: str) -> None:
        from datetime import datetime

        profile = self.get(platform, user_id)
        if profile:
            profile.last_seen = datetime.now(UTC).isoformat()
            profile.save()

    def list_all(self) -> list[UserProfile]:
        if not USER_DIR.exists():
            return []
        profiles: list[UserProfile] = []
        for path in USER_DIR.glob("*.json"):
            try:
                profiles.append(UserProfile(**json.loads(path.read_text())))
            except Exception:
                continue
        return profiles

    def remove(self, platform: str, user_id: str) -> bool:
        profile = self.get(platform, str(user_id))
        if profile:
            return profile.delete()
        return False

    def generate_invite_code(self, secret: str = "") -> str:
        from datetime import datetime

        ts = str(int(time.time()))
        key = (secret or os.urandom(16).hex()).encode()
        code = hmac.new(key, ts.encode(), hashlib.sha256).hexdigest()[:8].upper()
        invites = self._load_invites()
        expires = int(time.time()) + _INVITE_TTL
        invites[code] = {
            "expires": expires,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._save_invites(invites)
        return code

    def validate_invite(self, code: str) -> bool:
        invites = self._load_invites()
        entry = invites.get(code.upper())
        if not entry:
            return False
        if int(time.time()) > entry.get("expires", 0):
            del invites[code.upper()]
            self._save_invites(invites)
            return False
        return True

    def consume_invite(self, code: str) -> None:
        invites = self._load_invites()
        invites.pop(code.upper(), None)
        self._save_invites(invites)

    def _load_invites(self) -> dict:
        if not INVITES_FILE.exists():
            return {}
        try:
            return json.loads(INVITES_FILE.read_text())
        except Exception:
            return {}

    def _save_invites(self, invites: dict) -> None:
        INVITES_FILE.parent.mkdir(parents=True, exist_ok=True)
        INVITES_FILE.write_text(json.dumps(invites, indent=2))


def load_satellite_config() -> dict:
    if not SATELLITE_CONFIG.exists():
        return {}
    try:
        return json.loads(SATELLITE_CONFIG.read_text())
    except Exception:
        return {}


def save_satellite_config(config: dict) -> None:
    SATELLITE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SATELLITE_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False))
