from pydantic import BaseModel, ConfigDict # type: ignore

class AccountCreate(BaseModel):
    owner_name: str

class AccountOut(BaseModel):
    id: int
    owner_name: str
    balance: float
    model_config = ConfigDict(from_attributes=True)
