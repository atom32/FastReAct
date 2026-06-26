"""Inbound identity context and lightweight token verification helpers."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any


@dataclass
class IdentityContext:
    """Authenticated caller identity passed through FastReAct runtime boundaries."""

    tenant_key: str = ""
    user_key: str = ""
    subject: str = ""
    display_name: str = ""
    email: str = ""
    groups: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    auth_provider: str = "service_token"

    def to_metadata(self) -> dict[str, Any]:
        identity = {
            "tenant_key": self.tenant_key,
            "user_key": self.user_key,
            "subject": self.subject,
            "display_name": self.display_name,
            "email": self.email,
            "groups": list(self.groups),
            "roles": list(self.roles),
            "auth_provider": self.auth_provider,
        }
        return {
            "tenant_key": self.tenant_key,
            "user_key": self.user_key,
            "identity": identity,
        }


class IdentityVerificationError(ValueError):
    """Raised when inbound identity material cannot be trusted."""


def infer_tenant_key(user_key: str | None, tenant_key: str | None = None) -> str:
    if tenant_key:
        return tenant_key
    if user_key and ":" in user_key:
        return user_key.split(":", 1)[0]
    return ""


def list_claim(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def verify_hs256_jwt(
    token: str,
    secret: str,
    *,
    issuer: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """Verify a compact JWT signed with HS256 and return its payload claims."""
    parts = token.split(".")
    if len(parts) != 3:
        raise IdentityVerificationError("JWT must have three segments")
    header_segment, payload_segment, signature_segment = parts
    header = _decode_json_segment(header_segment)
    if header.get("alg") != "HS256":
        raise IdentityVerificationError("Only HS256 JWTs are supported by the lightweight verifier")

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    provided = _decode_segment(signature_segment)
    if not hmac.compare_digest(expected, provided):
        raise IdentityVerificationError("JWT signature is invalid")

    payload = _decode_json_segment(payload_segment)
    now = datetime.now(timezone.utc).timestamp()
    if "exp" in payload and now >= float(payload["exp"]):
        raise IdentityVerificationError("JWT has expired")
    if "nbf" in payload and now < float(payload["nbf"]):
        raise IdentityVerificationError("JWT is not valid yet")
    if issuer and payload.get("iss") != issuer:
        raise IdentityVerificationError("JWT issuer is invalid")
    if audience:
        audiences = list_claim(payload.get("aud"))
        if audience not in audiences:
            raise IdentityVerificationError("JWT audience is invalid")
    return payload


def _decode_json_segment(segment: str) -> dict[str, Any]:
    try:
        decoded = _decode_segment(segment)
        payload = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise IdentityVerificationError("JWT segment is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise IdentityVerificationError("JWT segment must decode to an object")
    return payload


def _decode_segment(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + padding)
    except ValueError as exc:
        raise IdentityVerificationError("JWT segment is not valid base64url") from exc
