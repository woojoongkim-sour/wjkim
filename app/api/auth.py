from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserLogin, Token, PasswordChange
)
from app.services.auth import (
    AuthService, get_current_user, get_current_active_user, get_admin_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Register a new user (admin only)."""
    existing = await db.execute(
        f"SELECT id FROM users WHERE email = '{user_data.email}' OR username = '{user_data.username}'"
    )
    if existing.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    user = await AuthService.create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        customer_id=user_data.customer_id,
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    return user


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token."""
    user = await AuthService.authenticate_user(
        db=db,
        username=credentials.username,
        password=credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None
    
    access_token, refresh_token = await AuthService.create_session(
        db=db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    result = await AuthService.refresh_access_token(db, refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    new_access_token, _ = result
    
    return Token(
        access_token=new_access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user info."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user info."""
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password."""
    from app.services.auth import verify_password, get_password_hash
    
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.hashed_password = get_password_hash(password_change.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    customer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List users (admin only)."""
    from sqlalchemy import select
    
    query = select(User)
    if customer_id:
        query = query.where(User.customer_id == customer_id)
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserUpdate,
    current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user (admin only)."""
    from sqlalchemy import select
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user
