from pydantic import BaseModel

class UserInfo(BaseModel):
    sub: str
    given_name: str
    family_name: str
    nickname: str
    name: str
    picture: str
    updated_at: str
    email: str
    email_verified: bool