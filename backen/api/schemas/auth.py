from pydantic import BaseModel


class LoginSchema(BaseModel):
    email: str
    password: str


class CreateUserSchema(BaseModel):
    email: str
    name: str = ""
    password: str
    ticket: str
