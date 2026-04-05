from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings


@dataclass
class AuthenticatedUser:
    username: str
    roles: list[str]
    subject: str
    auth_source: str


DEMO_USERS: dict[str, AuthenticatedUser] = {
    "clinician_anna": AuthenticatedUser(
        username="clinician_anna",
        roles=["clinician"],
        subject="dev-clinician-anna",
        auth_source="dev",
    ),
    "steward_mateo": AuthenticatedUser(
        username="steward_mateo",
        roles=["data_steward"],
        subject="dev-steward-mateo",
        auth_source="dev",
    ),
    "siteadmin_nora": AuthenticatedUser(
        username="siteadmin_nora",
        roles=["site_admin"],
        subject="dev-siteadmin-nora",
        auth_source="dev",
    ),
    "auditor_lee": AuthenticatedUser(
        username="auditor_lee",
        roles=["auditor"],
        subject="dev-auditor-lee",
        auth_source="dev",
    ),
}


def list_demo_users() -> list[dict[str, Any]]:
    return [
        {
            "username": user.username,
            "roles": user.roles,
            "auth_source": user.auth_source,
        }
        for user in DEMO_USERS.values()
    ]


security_scheme = HTTPBearer(auto_error=False)


def _forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message,
    )


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
    )


def _resolve_dev_user(x_demo_user: str | None, bearer_token: str | None) -> AuthenticatedUser:
    username = x_demo_user or settings.demo_default_user

    if bearer_token and bearer_token.startswith("dev-"):
        username = bearer_token.removeprefix("dev-")

    user = DEMO_USERS.get(username)
    if not user:
        raise _unauthorized(
            f"Unknown dev user '{username}'. Use one of: {', '.join(DEMO_USERS.keys())}"
        )
    return user


@lru_cache(maxsize=1)
def _load_jwks() -> dict[str, Any]:
    if not settings.resolved_jwks_url:
        raise _unauthorized("Keycloak JWKS URL is not configured.")
    response = httpx.get(settings.resolved_jwks_url, timeout=10.0)
    response.raise_for_status()
    return response.json()


def _decode_keycloak_token(token: str) -> AuthenticatedUser:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise _unauthorized("Invalid token header.") from exc

    jwks = _load_jwks()
    keys = jwks.get("keys", [])
    matching_key = next((key for key in keys if key.get("kid") == unverified_header.get("kid")), None)

    if not matching_key:
        raise _unauthorized("No matching signing key found for token.")

    try:
        payload = jwt.decode(
            token,
            matching_key,
            algorithms=[matching_key.get("alg", "RS256")],
            audience=settings.keycloak_client_id or None,
            options={"verify_aud": bool(settings.keycloak_client_id)},
        )
    except JWTError as exc:
        raise _unauthorized("Token validation failed.") from exc

    realm_access = payload.get("realm_access", {})
    roles = realm_access.get("roles", [])
    username = payload.get("preferred_username") or payload.get("sub") or "unknown_user"

    return AuthenticatedUser(
        username=username,
        roles=list(roles),
        subject=str(payload.get("sub", username)),
        auth_source="keycloak",
    )


def get_current_user(
    x_demo_user: str | None = Header(default=None, alias="X-Demo-User"),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> AuthenticatedUser:
    bearer_token = credentials.credentials if credentials else None

    if settings.auth_mode == "dev":
        return _resolve_dev_user(x_demo_user=x_demo_user, bearer_token=bearer_token)

    if settings.auth_mode == "keycloak":
        if not bearer_token:
            raise _unauthorized("Bearer token required.")
        return _decode_keycloak_token(bearer_token)

    raise _unauthorized(f"Unsupported auth mode '{settings.auth_mode}'.")


def require_roles(*allowed_roles: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    allowed = set(allowed_roles)

    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not allowed.intersection(user.roles):
            raise _forbidden(
                f"Role not permitted. Required one of: {', '.join(sorted(allowed))}"
            )
        return user

    return dependency