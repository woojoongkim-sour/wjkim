import logging
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserSession
from app.schemas.user import TokenData

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("user_id")
        username = payload.get("username")
        role = payload.get("role")
        customer_id = payload.get("customer_id")
        exp = datetime.fromtimestamp(payload.get("exp", 0))
        
        if not all([user_id, username, role, customer_id]):
            return None
        
        return TokenData(
            user_id=user_id,
            username=username,
            role=role,
            customer_id=customer_id,
            exp=exp
        )
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    token_data = decode_token(token)
    
    if token_data is None:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if current_user.role != "admin" and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


class AuthService:
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        
        user.last_login_at = datetime.utcnow()
        await db.commit()
        
        return user

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        username: str,
        password: str,
        customer_id: int,
        full_name: Optional[str] = None,
        role: str = "engineer"
    ) -> User:
        hashed_password = get_password_hash(password)
        
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            customer_id=customer_id,
            full_name=full_name,
            role=role
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user: User,
        user_agent: str = None,
        ip_address: str = None
    ) -> tuple[str, str]:
        import secrets
        session_id = secrets.token_hex(32)
        
        access_token = create_access_token({
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "customer_id": user.customer_id
        })
        
        refresh_token = create_refresh_token({
            "user_id": user.id,
            "session_id": session_id
        })
        
        session = UserSession(
            user_id=user.id,
            session_id=session_id,
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        db.add(session)
        await db.commit()
        
        return access_token, refresh_token

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession, refresh_token: str
    ) -> Optional[tuple[str, str]]:
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            if payload.get("type") != "refresh":
                return None
            
            user_id = payload.get("user_id")
            
            result = await db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == refresh_token,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
            session = result.scalar_one_or_none()
            
            if not session:
                return None
            
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                return None
            
            new_access_token = create_access_token({
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "customer_id": user.customer_id
            })
            
            return new_access_token, refresh_token
            
        except JWTError:
            return None
