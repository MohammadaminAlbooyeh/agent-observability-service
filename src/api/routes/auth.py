"""Exchange an admin API key for a short-lived JWT."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.middleware.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, is_admin_key

router = APIRouter()


class TokenRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest) -> TokenResponse:
    if not is_admin_key(body.api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API key")
    return TokenResponse(
        access_token=create_access_token("admin"),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
