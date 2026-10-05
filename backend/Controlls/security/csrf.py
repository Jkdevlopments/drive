import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


from fastapi import APIRouter, Request, Response


# =========================================================
# SAFE HTTP METHODS
# =========================================================

SAFE_METHODS = {
    "GET",
    "HEAD",
    "OPTIONS"
}


# =========================================================
# CSRF EXEMPT PATHS
# =========================================================

EXEMPT_PATHS = {
    "/auth/login",
    "/auth/refresh",
    "/auth/register",
    "/auth/csrf",
}


# =========================================================
# CSRF MIDDLEWARE
# =========================================================

class middle(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next
    ):

        # =================================================
        # EXEMPT PATHS
        # =================================================

        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)


        # =================================================
        # GET CSRF TOKEN FROM COOKIE
        # =================================================

        csrf = request.cookies.get("csrf")

        csrf_was_missing = csrf is None


        # =================================================
        # FIRST REQUEST
        # =================================================

        if csrf_was_missing:

            csrf = secrets.token_urlsafe(32)


        # =================================================
        # SAFE METHODS
        # =================================================

        if request.method in SAFE_METHODS:

            response = await call_next(request)

            # Only create/set CSRF cookie when it
            # did not already exist.
            if csrf_was_missing:

                response.set_cookie(
                    key="csrf",
                    value=csrf,
                    httponly=False,
                    secure=True,
                    samesite="none",
                    max_age=60 * 60 * 24 * 7,
                    path="/"
                )

            return response


        # =================================================
        # UNSAFE METHODS
        # POST / PUT / PATCH / DELETE
        # =================================================

        header_token = request.headers.get(
            "X-CSRF-Token"
        )


        # =================================================
        # DEBUG
        # =================================================

        print("CSRF COOKIE :", csrf)
        print("CSRF HEADER :", header_token)


        # =================================================
        # HEADER MISSING
        # =================================================

        if header_token is None:

            return JSONResponse(
                status_code=403,
                content={
                    "message": "CSRF token missing"
                }
            )


        # =================================================
        # TOKEN COMPARISON
        # =================================================

        try:

            valid = secrets.compare_digest(
                csrf,
                header_token
            )

        except (TypeError, ValueError):

            valid = False


        if not valid:

            return JSONResponse(
                status_code=403,
                content={
                    "message": "Invalid CSRF token"
                }
            )


        # =================================================
        # REQUEST
        # =================================================

        response = await call_next(request)


        # =================================================
        # IF CSRF DID NOT EXIST BEFORE,
        # SAVE THE NEW TOKEN
        # =================================================

        if csrf_was_missing:

            response.set_cookie(
                key="csrf",
                value=csrf,
                httponly=False,
                secure=True,
                samesite="none",
                max_age=60 * 60 * 24 * 7,
                path="/"
            )


        return response






r11 = APIRouter(prefix="/auth")


# =========================================================
# GET CSRF TOKEN
# =========================================================

@r11.get("/csrf")
def get_csrf(
    request: Request,
    response: Response
):
    # -----------------------------------------
    # Check existing CSRF cookie
    # -----------------------------------------

    csrf = request.cookies.get("csrf")

    # -----------------------------------------
    # Create token only if it does not exist
    # -----------------------------------------

    if csrf is None:

        csrf = secrets.token_urlsafe(32)

        response.set_cookie(
            key="csrf",
            value=csrf,
            httponly=False,
            secure=True,
            samesite="none",
            max_age=60 * 60 * 24 * 7,
            path="/"
        )

    # -----------------------------------------
    # Send same token to frontend
    # -----------------------------------------

    return {
        "csrf_token": csrf
    }