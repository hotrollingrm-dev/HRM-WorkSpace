from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import SessionToken, User

COOKIE = "hrm_session"
_ITER = 200_000

RANK = {"viewer": 0, "leader": 1, "foreman": 2, "admin": 3}


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), _ITER)
    return f"pbkdf2${_ITER}${salt}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, it, salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False


def create_session(db: Session, user: User) -> str:
    tok = secrets.token_urlsafe(32)
    exp = (datetime.now().astimezone() + timedelta(hours=config.SESSION_HOURS)).isoformat()
    db.add(SessionToken(token=tok, user_id=user.id, expires_at=exp))
    db.commit()
    return tok


def current_user(hrm_session: str | None = Cookie(default=None),
                 db: Session = Depends(get_db)) -> User:
    if not hrm_session:
        raise HTTPException(401, "กรุณาเข้าสู่ระบบ")
    st = db.get(SessionToken, hrm_session)
    if not st or datetime.fromisoformat(st.expires_at) < datetime.now().astimezone():
        raise HTTPException(401, "เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่")
    user = db.get(User, st.user_id)
    if not user or not user.active:
        raise HTTPException(401, "บัญชีถูกปิดใช้งาน")
    return user


def require(min_role: str):
    def dep(user: User = Depends(current_user)) -> User:
        if RANK.get(user.role, -1) < RANK[min_role]:
            raise HTTPException(403, "สิทธิ์ไม่เพียงพอสำหรับการทำรายการนี้")
        return user
    return dep
