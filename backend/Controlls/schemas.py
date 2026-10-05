from pydantic import BaseModel,EmailStr
from typing import Optional
class RegisterRequest(BaseModel):
    name:str
    age:Optional[int]=None
    email:EmailStr
    password:str

class RegisterResponse(BaseModel):
    status_code:int
    msg:str

class LoginRequest(BaseModel):
    email:EmailStr
    password:str

class LoginResponse(BaseModel):
    status:str

class CreateFolderRequest(BaseModel): 
    name: str 
    parent_id: int | None = None

class FolderResponse(BaseModel):
     id: int 
     
     name: str 
     parent_id: int | None = None
     class Config: from_attributes = True
class RenameRequest(BaseModel): name: str
class MoveRequest(BaseModel): folder_id: Optional[int] = None