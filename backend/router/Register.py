from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from Controlls.schemas import RegisterRequest,RegisterResponse
from Controlls.Database.init import get_db

from Controlls.Database.table import Users
from Controlls.security.passwdsafty import hashing

r1=APIRouter(prefix="/auth",
             tags=["auth"])

@r1.post("/register")
def Register(data:RegisterRequest,db:Session=Depends(get_db)
             ):
    passwd=hashing(data.password)
    user=db.query(Users).filter(Users.email==data.email).first()
    if user is not None:
        raise HTTPException(
            status_code=409,
            detail="user already exists"
        )
    
    new_user=Users(
        name=data.name,
        age=data.age,
        email=data.email,
        password=passwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RegisterResponse(status_code=200,msg="Success")
   




