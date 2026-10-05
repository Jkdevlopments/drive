import secrets

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from Controlls.Database.init import get_db
from Controlls.Database.table import Users
from Controlls.schemas import LoginRequest
from Controlls.security.passwdsafty import verify_passwd
from Controlls.security.SessionHandler import (
    create_token,
    create_refresh_token
)


r2 = APIRouter(prefix="/auth")


@r2.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    # =====================================================
    # FIND USER
    # =====================================================

    user = db.query(Users).filter(
        Users.email == data.email
    ).first()


    # =====================================================
    # USER NOT FOUND
    # =====================================================

    if user is None:

        response = JSONResponse(
            status_code=404,
            content={
                "detail": "user not found"
            }
        )

        response.delete_cookie(
            key="access_token",
            path="/"
        )

        response.delete_cookie(
            key="refresh_token",
            path="/"
        )

        response.delete_cookie(
            key="csrf",
            path="/"
        )

        return response


    # =====================================================
    # WRONG PASSWORD
    # =====================================================

    if not verify_passwd(
        data.password,
        user.password
    ):

        response = JSONResponse(
            status_code=401,
            content={
                "detail": "invalid password"
            }
        )

        response.delete_cookie(
            key="access_token",
            path="/"
        )

        response.delete_cookie(
            key="refresh_token",
            path="/"
        )

        response.delete_cookie(
            key="csrf",
            path="/"
        )

        return response


    # =====================================================
    # CREATE ACCESS TOKEN
    # =====================================================

    access_token = create_token(
        user.name,
        user.email
    )


    # =====================================================
    # CREATE REFRESH TOKEN
    # =====================================================

    refresh_token = create_refresh_token(
        user.name,
        user.email
    )


    # =====================================================
    # CREATE CSRF TOKEN
    # =====================================================

    csrf_token = secrets.token_urlsafe(32)


    # =====================================================
    # SUCCESS RESPONSE
    # =====================================================

    response = JSONResponse(
        status_code=200,
        content={
            "status": "login success"
        }
    )


    # =====================================================
    # ACCESS TOKEN COOKIE
    # =====================================================

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=15 * 60,
        path="/"
    )


    # =====================================================
    # REFRESH TOKEN COOKIE
    # =====================================================

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * 60 * 24 * 7,
        path="/"
    )


    # =====================================================
    # CSRF COOKIE
    # =====================================================

    response.set_cookie(
        key="csrf",
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="none",
        max_age=60 * 60 * 24 * 7,
        path="/"
    )


    return response