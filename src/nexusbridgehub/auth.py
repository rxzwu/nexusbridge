"""JWT authentication for workers and controllers."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

import jwt

from nexusbridgehub.protocol import Role


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub: str
    role: Role
    project_id: str
    user_id: str
    exp: int
    iat: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenClaims":
        return cls(
            sub=str(data["sub"]),
            role=Role(data["role"]),
            project_id=str(data["project_id"]),
            user_id=str(data["user_id"]),
            exp=int(data["exp"]),
            iat=int(data["iat"]),
        )


class AuthManager:
    def __init__(self, secret: str, *, algorithm: str = "HS256", ttl_seconds: int = 86_400) -> None:
        if not secret or len(secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = ttl_seconds
        self._pair_codes: dict[str, dict[str, str]] = {}

    def create_token(
        self,
        *,
        role: Role,
        project_id: str,
        user_id: str,
        ttl_seconds: int | None = None,
    ) -> str:
        now = int(time.time())
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        payload = {
            "sub": f"{project_id}:{user_id}:{role.value}",
            "role": role.value,
            "project_id": project_id,
            "user_id": user_id,
            "iat": now,
            "exp": now + ttl,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> TokenClaims:
        data = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        return TokenClaims.from_dict(data)

    def create_pair_code(self, *, project_id: str, user_id: str, ttl_seconds: int = 600) -> str:
        """
        Create a pair code for worker authentication.

        Args:
            project_id: Project identifier
            user_id: User identifier
            ttl_seconds: Time to live in seconds (default: 600 = 10 minutes)

        Returns:
            8-character pair code (uppercase alphanumeric)
        """
        code = secrets.token_urlsafe(6).upper()[:8]
        self._pair_codes[code] = {
            "project_id": project_id,
            "user_id": user_id,
            "expires_at": str(int(time.time()) + ttl_seconds),
        }
        return code

    def redeem_pair_code(self, code: str) -> tuple[str, str] | None:
        entry = self._pair_codes.pop(code.upper(), None)
        if not entry:
            return None
        if int(entry["expires_at"]) < int(time.time()):
            return None
        return entry["project_id"], entry["user_id"]
