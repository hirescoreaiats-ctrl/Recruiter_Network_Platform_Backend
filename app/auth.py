from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

security = HTTPBearer(auto_error=False)
ROLES = {"requirement_vendor", "sourcing_partner", "candidate"}


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise HTTPException(422, "Password must contain at least 8 characters")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def token_for(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    if not user or not user.is_active:
        raise HTTPException(401, "Account unavailable")
    return user


def require_role(*roles: str):
    def dependency(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "This account is not authorized for this action")
        return user
    return dependency

