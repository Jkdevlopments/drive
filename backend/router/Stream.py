from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from Controlls.security.SessionHandler import get_user
from Controlls.Database.init import get_db
from Controlls.Database.table import Users, StorageFile

from pathlib import Path


stream = APIRouter(
    prefix="/video",
    tags=["Video"]
)


# ============================================================
# GET CURRENT USER
# ============================================================

def get_current_user(auth_user, db):

    username, email = auth_user

    user = (
        db.query(Users)
        .filter(Users.email == email)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


# ============================================================
# STREAM SELECTED VIDEO
# ============================================================

@stream.get("/{file_id}")
def streaming(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    # --------------------------------------------------------
    # Current user
    # --------------------------------------------------------

    user = get_current_user(
        auth_user,
        db
    )

    # --------------------------------------------------------
    # Get file
    # --------------------------------------------------------

    file = (
        db.query(StorageFile)
        .filter(
            StorageFile.id == file_id,
            StorageFile.user_id == user.id
        )
        .first()
    )

    if file is None:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    # --------------------------------------------------------
    # Physical path
    # --------------------------------------------------------

    path = Path(file.path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Physical file not found"
        )

    # --------------------------------------------------------
    # Only allow video
    # --------------------------------------------------------

    video_extensions = {
        ".mp4",
        ".webm",
        ".ogg",
        ".mov",
        ".m4v"
    }

    if path.suffix.lower() not in video_extensions:

        raise HTTPException(
            status_code=400,
            detail="Selected file is not a video"
        )

    # --------------------------------------------------------
    # File size
    # --------------------------------------------------------

    file_size = path.stat().st_size

    # --------------------------------------------------------
    # Range
    # --------------------------------------------------------

    range_header = request.headers.get("range")

    # ========================================================
    # FULL FILE
    # ========================================================

    if range_header is None:

        def video_stream():

            with open(path, "rb") as buffer:

                while True:

                    chunk = buffer.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    yield chunk

        return StreamingResponse(
            video_stream(),
            media_type=file.mime_type or "video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            }
        )

    # ========================================================
    # RANGE REQUEST
    # ========================================================

    try:

        range_value = range_header.replace(
            "bytes=",
            ""
        )

        start_str, end_str = range_value.split("-")

        start = int(start_str)

        if end_str:
            end = int(end_str)
        else:
            end = file_size - 1

    except (ValueError, AttributeError):

        raise HTTPException(
            status_code=416,
            detail="Invalid range"
        )

    # --------------------------------------------------------
    # Validate range
    # --------------------------------------------------------

    if start < 0 or start >= file_size:

        raise HTTPException(
            status_code=416,
            detail="Range not satisfiable"
        )

    end = min(
        end,
        file_size - 1
    )

    if end < start:

        raise HTTPException(
            status_code=416,
            detail="Range not satisfiable"
        )

    content_length = end - start + 1

    # ========================================================
    # RANGE STREAM
    # ========================================================

    def range_video():

        with open(path, "rb") as buffer:

            buffer.seek(start)

            remaining = content_length

            while remaining > 0:

                chunk_size = min(
                    1024 * 1024,
                    remaining
                )

                chunk = buffer.read(
                    chunk_size
                )

                if not chunk:
                    break

                yield chunk

                remaining -= len(chunk)

    # ========================================================
    # RESPONSE
    # ========================================================

    return StreamingResponse(
        range_video(),
        status_code=206,
        media_type=file.mime_type or "video/mp4",
        headers={
            "Content-Range":
                f"bytes {start}-{end}/{file_size}",

            "Accept-Ranges": "bytes",

            "Content-Length":
                str(content_length),
        }
    )