from typing import Optional
import jwt
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config.settings import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    # 1. Try JWT Bearer token if provided
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(
                credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub")
            if user_id:
                return str(user_id)
        except Exception:
            pass

    # 2. Try X-Farmer-ID or farmer_id headers
    farmer_header = (
        request.headers.get("x-farmer-id")
        or request.headers.get("farmer_id")
        or request.headers.get("farmer-id")
    )
    if farmer_header:
        return str(farmer_header)

    # 3. Try farmer_id query parameter
    farmer_query = request.query_params.get("farmer_id")
    if farmer_query:
        return str(farmer_query)

    # Default fallback for anonymous/QR mode
    return "anonymous"
