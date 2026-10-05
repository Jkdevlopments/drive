from jose import jwt,JWSError,ExpiredSignatureError,JWTError
from datetime import datetime,timedelta,timezone

from fastapi import Depends,HTTPException,APIRouter
from fastapi import Cookie,Response,Depends


import os
from dotenv import load_dotenv

load_dotenv()
key=os.getenv("SECRET_KEY")
alg=os.getenv("ALGORITHM")

refresh=APIRouter(prefix="/auth")
r10=APIRouter(prefix="/auth")




@refresh.post("/refresh")
def refresh_token(respose:Response,refresh:str | None=Cookie(default=None,alias="refresh_token")):
    if refresh is None:
        raise HTTPException(
            status_code=401,
            detail="refresh token missing"
        )
    try:
        payload=jwt.decode(
            refresh,
            key=key,
            algorithms=[alg]
        )
        user=payload.get("sub")
        email=payload.get("email")
        type=payload.get("type")
        if user is None or email is None:
            raise HTTPException(
                status_code=401,
                detail="invalid"

            )
        if type!="refresh":
            raise HTTPException(
                status_code=401,
                detail="invalid token type")
        new=create_token(user,email)
        respose.set_cookie(
            key="access_token",
            value=new,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=15*60

        )
        return {
            "message": "Access token refreshed"
        }
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Refresh token expired. Login again."
        )

    except JWSError:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    








def create_token(uname:str,email:str):
    expire=datetime.now(timezone.utc)+timedelta(days=5)
    payload={
        "sub":uname,
        "email":email,
        "type":"access",
        "exp":expire
    }
    return jwt.encode(
        payload,
        key=key,
        algorithm=alg


    )


def create_refresh_token(uname:str,email:str):
    expire=datetime.now(timezone.utc)+timedelta(days=7)
    payload={"sub":uname,
             "email":email,
             "type":"refresh",
             "exp":expire}
    return jwt.encode(payload,key=key,algorithm=alg)
def verify_token(token:str):
    
    
    payload=jwt.decode(token,key=key,algorithms=[alg])
    username=payload.get("sub")
    email=payload.get("email")
    if username is None or email is None:
        raise HTTPException(
                status_code=401,
                detail="not authenticated"
            )

    return username,email
    
   
    


def get_user(response:Response,access_token:str |None= Cookie(default=None)):
    if access_token is None:
        raise HTTPException(
            status_code=401,detail="not authenticated"
        )
    try:
        return verify_token(access_token)
    except ExpiredSignatureError:
        response.delete_cookie(
            key="access_token"
        )
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )
    except JWSError:
        response.delete_cookie(
            "access_token"
        )
        
        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except JWTError:
        raise HTTPException(
                    status_code=401,
                    detail="not authenticated"
                )




@r10.get("/me")
def current_user(user=Depends(get_user)):
    username,email=user
    return {
        "authenticated":True,
        "username":username,
        "email":email
    }
