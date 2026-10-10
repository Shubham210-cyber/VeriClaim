"""Customer upload tokens: random, hashed at rest, expiring, revocable, claim-scoped."""
import hashlib
import secrets
import time
from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.models import UploadRequest, utcnow
from app.errors import AppError

_fails: dict[str, list[float]] = {}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(db: Session, claim_id: str, items: list[dict], hours: int, max_uploads: int) -> tuple[str, UploadRequest]:
    token = secrets.token_urlsafe(32)
    req = UploadRequest(claim_id=claim_id, token_hash=hash_token(token), requested_items=items,
                        expires_at=utcnow() + timedelta(hours=hours), max_uploads=max_uploads)
    db.add(req)
    db.flush()
    return token, req


def _throttle(client: str) -> None:
    now = time.time()
    recent = [t for t in _fails.get(client, []) if now - t < 60]
    _fails[client] = recent
    if len(recent) >= 10:
        raise AppError(429, "TOO_MANY_ATTEMPTS", "Too many invalid attempts. Try again later.")


def resolve(db: Session, token: str | None, client: str = "?", for_upload: bool = False) -> UploadRequest:
    _throttle(client)
    req = db.query(UploadRequest).filter_by(token_hash=hash_token(token)).first() if token else None
    if req is None:
        _fails.setdefault(client, []).append(time.time())
        raise AppError(404, "INVALID_LINK", "This upload link is not valid.")
    if req.revoked_at is not None:
        raise AppError(403, "LINK_REVOKED", "This upload link has been revoked.")
    if req.expires_at <= utcnow():
        raise AppError(403, "LINK_EXPIRED", "This upload link has expired.")
    if for_upload and req.upload_count >= req.max_uploads:
        raise AppError(403, "LINK_EXHAUSTED", "The upload limit for this link has been reached.")
    return req
