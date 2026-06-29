from pydantic import BaseModel, Field

# NOTE: email is a plain str (not pydantic EmailStr) on purpose — EmailStr pulls
# in the email-validator package, which isn't in requirements. Swap to EmailStr
# if you add that dependency and want stricter validation.


class UserCreate(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
