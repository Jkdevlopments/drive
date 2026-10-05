from fastapi import APIRouter, Response

logou = APIRouter(prefix="/auth")


@logou.post("/logout")
def logout(response: Response):

    print("LOGOUT START")

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

    print("LOGOUT END")

    return {
        "message": "logout successful"
    }