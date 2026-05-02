"""
/auth — Sovereign Identity Provider endpoints.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

try:
    from jose import jwt, jwk
    from passlib.context import CryptContext
except ImportError:
    jwt = None
    CryptContext = None

from sensory.identity_utils import ensure_keys_exist

logger = logging.getLogger("zana.identity")

router = APIRouter(tags=["Identity"])

# Configuration
ZANA_CONFIG_DIR = Path.home() / ".config" / "zana"
ZANA_KEYS_DIR = ZANA_CONFIG_DIR / "keys"

# Ensure keys exist on module load
if jwt:
    ensure_keys_exist(ZANA_KEYS_DIR)
    _priv_key_data = (ZANA_KEYS_DIR / "private_key.pem").read_bytes()
    _pub_key_data = (ZANA_KEYS_DIR / "public_key.pem").read_bytes()
    _jwk_key = jwk.construct(_pub_key_data, algorithm="RS256")
    
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") if CryptContext else None

# ── Database integration (mocked for local first boot or actual connection) ──

PG_HOST = os.getenv("ZANA_PG_HOST", "localhost")
PG_PORT = int(os.getenv("ZANA_PG_PORT", "55433"))
PG_DB = os.getenv("ZANA_PG_DB", "zana")
PG_USER = os.getenv("ZANA_PG_USER", "zana")
PG_PASS = os.getenv("ZANA_PG_PASSWORD", "zana_pass")

_pool = None

async def _get_pool():
    global _pool
    if _pool is None:
        try:
            import asyncpg  # type: ignore
            _pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=1,
                max_size=5,
            )
        except ImportError:
            logger.warning("asyncpg not installed. Identity DB queries will fail.")
    return _pool


class TokenResponse(BaseModel):
    access_token: str
    id_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/auth/token", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login, getting an access token for future requests"""
    if not jwt:
        raise HTTPException(status_code=500, detail="JWT/Cryptography libraries missing")

    pool = await _get_pool()
    user = None
    if pool:
        async with pool.acquire() as conn:
            # First try to find the user by username/email
            user = await conn.fetchrow("SELECT id, username, password_hash, is_master FROM users WHERE username = $1 OR email = $1", form_data.username)
            
            if not user and form_data.username == "admin" and form_data.password == "admin":
                # Fallback bootstrap logic: If no master exists, create one using admin/admin
                master_exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE is_master = TRUE)")
                if not master_exists:
                    hashed_pwd = pwd_context.hash("admin")
                    user_id = await conn.fetchval(
                        "INSERT INTO users (username, password_hash, is_master) VALUES ($1, $2, TRUE) RETURNING id",
                        "admin", hashed_pwd
                    )
                    user = {"id": user_id, "username": "admin", "password_hash": hashed_pwd, "is_master": True}
            
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user["password_hash"] and not pwd_context.verify(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    now = datetime.utcnow()
    expires_delta = timedelta(hours=24)
    exp = now + expires_delta
    
    # ID Token (OIDC)
    id_token_payload = {
        "iss": os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446"),
        "sub": str(user["id"]),
        "aud": "zana-client",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "preferred_username": user["username"]
    }
    
    # Access Token (API auth)
    access_token_payload = {
        "iss": os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446"),
        "sub": str(user["id"]),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "scopes": ["admin"] if user["is_master"] else ["user"]
    }

    # Extract Key ID from JWK for header
    headers = {"kid": _jwk_key.to_dict().get("kid", "zana-root")}
    
    id_token = jwt.encode(id_token_payload, _priv_key_data, algorithm="RS256", headers=headers)
    access_token = jwt.encode(access_token_payload, _priv_key_data, algorithm="RS256", headers=headers)

    return TokenResponse(
        access_token=access_token,
        id_token=id_token,
        expires_in=int(expires_delta.total_seconds())
    )


class SocialLoginRequest(BaseModel):
    provider: str
    provider_id: str
    email: str
    username: str


@router.post("/auth/social", response_model=TokenResponse)
async def social_login(req: SocialLoginRequest):
    """
    Hybrid Sovereign Auth: Exchange a verified social identity for a local ZANA token.
    If the provider_id is new, it creates or links the local user.
    """
    if not jwt:
        raise HTTPException(status_code=500, detail="JWT/Cryptography libraries missing")

    pool = await _get_pool()
    if not pool:
        raise HTTPException(status_code=500, detail="Identity Database not ready")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Check if this social identity is already linked
            user_id = await conn.fetchval(
                "SELECT user_id FROM user_identities WHERE provider = $1 AND provider_id = $2",
                req.provider, req.provider_id
            )
            
            if not user_id:
                # 2. Check if email exists to link to an existing local account
                user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", req.email)
                
                if not user_id:
                    # 3. Create a brand new local ZANA ID (password is null)
                    user_id = await conn.fetchval(
                        "INSERT INTO users (username, email) VALUES ($1, $2) ON CONFLICT DO NOTHING RETURNING id",
                        req.username, req.email
                    )
                    if not user_id:
                        # Fallback for username collision (append part of the provider ID)
                        fallback_user = f"{req.username}_{req.provider_id[:6]}"
                        user_id = await conn.fetchval(
                            "INSERT INTO users (username, email) VALUES ($1, $2) RETURNING id",
                            fallback_user, req.email
                        )
                
                # 4. Link the new or existing local user to this social identity
                await conn.execute(
                    "INSERT INTO user_identities (user_id, provider, provider_id) VALUES ($1, $2, $3)",
                    user_id, req.provider, req.provider_id
                )

            # Fetch the final user info to construct the token
            user = await conn.fetchrow("SELECT id, username, is_master FROM users WHERE id = $1", user_id)

    if not user:
        raise HTTPException(status_code=500, detail="Sovereign Identity linking failed")

    # Generate tokens
    now = datetime.utcnow()
    expires_delta = timedelta(hours=24)
    exp = now + expires_delta
    
    # Extract Key ID from JWK for header
    headers = {"kid": _jwk_key.to_dict().get("kid", "zana-root")}

    # ID Token (OIDC)
    id_token_payload = {
        "iss": os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446"),
        "sub": str(user["id"]),
        "aud": "zana-client",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "preferred_username": user["username"],
        "auth_provider": req.provider
    }
    
    # Access Token (API auth)
    access_token_payload = {
        "iss": os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446"),
        "sub": str(user["id"]),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "scopes": ["admin"] if user["is_master"] else ["user"]
    }
    
    id_token = jwt.encode(id_token_payload, _priv_key_data, algorithm="RS256", headers=headers)
    access_token = jwt.encode(access_token_payload, _priv_key_data, algorithm="RS256", headers=headers)

    return TokenResponse(
        access_token=access_token,
        id_token=id_token,
        expires_in=int(expires_delta.total_seconds())
    )


@router.get("/.well-known/jwks.json")
async def jwks():
    """Return public keys for JWT validation."""
    if not jwt:
        return {"keys": []}
    
    key_dict = _jwk_key.to_dict()
    key_dict["use"] = "sig"
    key_dict["kid"] = "zana-root"
    return {"keys": [key_dict]}


@router.get("/auth/userinfo")
async def userinfo():
    """Placeholder for OIDC userinfo endpoint."""
    return {"sub": "unknown", "message": "Requires Bearer token validation implementation."}
