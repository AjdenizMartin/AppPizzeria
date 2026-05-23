from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(default="", max_length=120)
    address_line: str = Field(default="", max_length=200)
    city: str = Field(default="", max_length=120)
    postal_code: str = Field(default="", max_length=40)
    phone: str = Field(default="", max_length=40)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_admin: bool
    role: str
    full_name: str | None = None
    address_line: str | None = None
    city: str | None = None
    postal_code: str | None = None
    phone: str | None = None


class UserProfileUpdate(BaseModel):
    full_name: str = Field(default="", max_length=120)
    address_line: str = Field(default="", max_length=200)
    city: str = Field(default="", max_length=120)
    postal_code: str = Field(default="", max_length=40)
    phone: str = Field(default="", max_length=40)


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(owner|manager|staff|customer)$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    
