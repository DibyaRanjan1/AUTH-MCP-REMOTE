from typing import Optional

from pydantic import BaseModel


class UserInfo(BaseModel):
    """Auth0 user profile from /userinfo."""

    sub: str
    name: str
    email: str
    email_verified: bool = False
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    nickname: Optional[str] = None
    picture: Optional[str] = None
    updated_at: Optional[str] = None