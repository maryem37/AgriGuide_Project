import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from models.farmer import Farmer
from schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )

    def create_access_token(self, user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {"sub": user_id, "exp": expire}
        return jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    async def register(self, data: UserCreate) -> TokenResponse:
        existing = await self.db.execute(
            select(Farmer).where(Farmer.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        farmer = Farmer(
            name=data.name,
            email=data.email,
            password_hash=self.hash_password(data.password),
            region=data.region,
        )
        self.db.add(farmer)
        await self.db.commit()
        await self.db.refresh(farmer)

        token = self.create_access_token(farmer.id)
        user = UserResponse(
            id=farmer.id,
            name=farmer.name,
            email=farmer.email,
            region=farmer.region,
        )
        logger.info(f"New user registered: {farmer.email}")
        return TokenResponse(access_token=token, user=user)

    async def login(self, data: UserLogin) -> TokenResponse:
        result = await self.db.execute(select(Farmer).where(Farmer.email == data.email))
        farmer = result.scalar_one_or_none()

        if not farmer or not self.verify_password(data.password, farmer.password_hash):
            raise ValueError("Invalid email or password")

        token = self.create_access_token(farmer.id)
        user = UserResponse(
            id=farmer.id,
            name=farmer.name,
            email=farmer.email,
            region=farmer.region,
        )
        logger.info(f"User logged in: {farmer.email}")
        return TokenResponse(access_token=token, user=user)

    async def get_current_user(self, user_id: str) -> Farmer:
        result = await self.db.execute(select(Farmer).where(Farmer.id == user_id))
        farmer = result.scalar_one_or_none()
        if not farmer:
            raise ValueError("User not found")
        return farmer

    async def update_device_token(self, user_id: str, device_token: str) -> None:
        result = await self.db.execute(select(Farmer).where(Farmer.id == user_id))
        farmer = result.scalar_one_or_none()
        if farmer:
            farmer.device_token = device_token
            await self.db.commit()
