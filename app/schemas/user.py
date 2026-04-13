from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_admin: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    
