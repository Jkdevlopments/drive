from pathlib import Path 
from uuid import uuid4 
from fastapi import ( 
    APIRouter, 
    Depends, 
    HTTPException, 
    Request 
) 
from fastapi.responses import ( 
    FileResponse, 
    StreamingResponse 
) 
from sqlalchemy.orm import Session 
 
from Controlls.security.SessionHandler import get_user 
from Controlls.Database.init import get_db 
from Controlls.Database.table import ( 
    Users, 
    StorageFile, 
    StorageFolder 
) 
 
 
sharing = APIRouter( 
    prefix="/share", 
    tags=["Sharing"] 
) 
 
 
CHUNK_SIZE = 1024 * 1024 
 
 
# ========================================================= 
# CURRENT USER 
# ========================================================= 
 
def get_current_user(auth_user, db: Session): 
 
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
 
 
# ========================================================= 
# OWNER HELPERS 
# ========================================================= 
 
def get_owned_file( 
    file_id: int, 
    user_id: int, 
    db: Session 
): 
 
    file = ( 
        db.query(StorageFile) 
        .filter( 
            StorageFile.id == file_id, 
            StorageFile.user_id == user_id 
        ) 
        .first() 
    ) 
 
    if file is None: 
        raise HTTPException( 
            status_code=404, 
            detail="File not found" 
        ) 
 
    return file 
 
 
def get_owned_folder( 
    folder_id: int, 
    user_id: int, 
    db: Session 
): 
 
    folder = ( 
        db.query(StorageFolder) 
        .filter( 
            StorageFolder.id == folder_id, 
            StorageFolder.user_id == user_id 
        ) 
        .first() 
    ) 
 
    if folder is None: 
        raise HTTPException( 
            status_code=404, 
            detail="Folder not found" 
        ) 
 
    return folder 
 
 
# ========================================================= 
# FILE SHARE 
# ========================================================= 
 
@sharing.post("/file/{file_id}") 
def create_file_share( 
    file_id: int, 
    db: Session = Depends(get_db), 
    auth_user=Depends(get_user) 
): 
 
    user = get_current_user(auth_user, db) 
 
    file = get_owned_file( 
        file_id, 
        user.id, 
        db 
    ) 
 
    # Already shared 
    if file.is_shared and file.share_id: 
 
        return { 
            "success": True, 
            "share_id": file.share_id, 
            "permission": file.share_permission, 
            "is_shared": True 
        } 
 
    share_id = str(uuid4()) 
 
    file.share_id = share_id 
    file.is_shared = True 
    file.share_permission = "viewer" 
 
    db.commit() 
    db.refresh(file) 
 
    return { 
        "success": True, 
        "share_id": file.share_id, 
        "permission": file.share_permission, 
        "is_shared": True 
    } 
 
 
# ========================================================= 
# STOP FILE SHARE 
# ========================================================= 
 
@sharing.delete("/file/{file_id}") 
def stop_file_share( 
    file_id: int, 
    db: Session = Depends(get_db), 
    auth_user=Depends(get_user) 
): 
 
    user = get_current_user(auth_user, db) 
 
    file = get_owned_file( 
        file_id, 
        user.id, 
        db 
    ) 
 
    file.is_shared = False 
    file.share_id = None 
 
    db.commit() 
 
    return { 
        "success": True, 
        "message": "File sharing stopped" 
    } 
 
 
# ========================================================= 
# FILE SHARE STATUS 
# ========================================================= 
 
@sharing.get("/file/{file_id}/status") 
def file_share_status( 
    file_id: int, 
    db: Session = Depends(get_db), 
    auth_user=Depends(get_user) 
): 
 
    user = get_current_user(auth_user, db) 
 
    file = get_owned_file( 
        file_id, 
        user.id, 
        db 
    ) 
 
    return { 
        "is_shared": file.is_shared, 
        "share_id": file.share_id, 
        "permission": file.share_permission 
    } 
 
 
# ========================================================= 
# FOLDER SHARE 
# ========================================================= 
 
@sharing.post("/folder/{folder_id}") 
def create_folder_share( 
    folder_id: int, 
    db: Session = Depends(get_db), 
    auth_user=Depends(get_user) 
): 
 
    user = get_current_user(auth_user, db) 
 
    folder = get_owned_folder( 
        folder_id, 
        user.id, 
        db 
    ) 
 
    # Already shared 
    if folder.is_shared and folder.share_id: 
 
        return { 
            "success": True, 
            "share_id": folder.share_id, 
            "permission": folder.share_permission, 
            "is_shared": True 
        } 
 
    share_id = str(uuid4()) 
 
    folder.share_id = share_id 
    folder.is_shared = True 
    folder.share_permission = "viewer" 
 
    db.commit() 
    db.refresh(folder) 
 
    return { 
        "success": True, 
        "share_id": folder.share_id, 
        "permission": folder.share_permission, 
        "is_shared": True 
    } 
 
 
# ========================================================= 
# STOP FOLDER SHARE 
# ========================================================= 
 
@sharing.delete("/folder/{folder_id}") 
def stop_folder_share( 
    folder_id: int, 
    db: Session = Depends(get_db), 
    auth_user=Depends(get_user) 
): 
 
    user = get_current_user(auth_user, db) 
 
    folder = get_owned_folder( 
        folder_id, 
        user.id, 
        db 
    ) 
 
    folder.is_shared = False 
    folder.share_id = None 
 
    db.commit() 
 
    return { 
        "success": True, 
        "message": "Folder sharing stopped" 
    } 
 
 
# ========================================================= 
# FOLDER SHARE STATUS 
# ========================================================= 
 
@sharing.get("/folder/{folder_id}/status") 
def folder_share_status( 
    folder_id: int, 
    db: Session = Depends(get_db), 
    auth_user=Depends(get_user) 
): 
 
    user = get_current_user(auth_user, db) 
 
    folder = get_owned_folder( 
        folder_id, 
        user.id, 
        db 
    ) 
 
    return { 
        "is_shared": folder.is_shared, 
        "share_id": folder.share_id, 
        "permission": folder.share_permission 
    } 
 
 
# ========================================================= 
# PUBLIC FILE INFO 
# ========================================================= 
 
@sharing.get("/public/file/{share_id}") 
def public_file_info( 
    share_id: str, 
    db: Session = Depends(get_db) 
): 
 
    file = ( 
        db.query(StorageFile) 
        .filter( 
            StorageFile.share_id == share_id, 
            StorageFile.is_shared == True 
        ) 
        .first() 
    ) 
 
    if file is None: 
        raise HTTPException( 
            status_code=404, 
            detail="Shared file not found" 
        ) 
 
    return { 
        "id": file.id, 
        "name": file.name, 
        "size": file.size, 
        "mime_type": file.mime_type, 
        "permission": file.share_permission 
    } 
 
 
# ========================================================= 
# PUBLIC FILE DOWNLOAD 
# ========================================================= 
 
@sharing.get("/public/file/{share_id}/download") 
def public_file_download( 
    share_id: str, 
    db: Session = Depends(get_db) 
): 
 
    file = ( 
        db.query(StorageFile) 
        .filter( 
            StorageFile.share_id == share_id, 
            StorageFile.is_shared == True 
        ) 
        .first() 
    ) 
 
    if file is None: 
        raise HTTPException( 
            status_code=404, 
            detail="Shared file not found" 
        ) 
 
    path = Path(file.path) 
 
    if not path.exists(): 
        raise HTTPException( 
            status_code=404, 
            detail="Physical file not found" 
        ) 
 
    return FileResponse( 
        path=path, 
        media_type=file.mime_type or "application/octet-stream", 
        filename=file.name 
    ) 
 
 
# ========================================================= 
# PUBLIC VIDEO STREAM 
# ========================================================= 
 
@sharing.get("/public/file/{share_id}/stream") 
def public_file_stream( 
    share_id: str, 
    request: Request, 
    db: Session = Depends(get_db) 
): 
 
    file = ( 
        db.query(StorageFile) 
        .filter( 
            StorageFile.share_id == share_id, 
            StorageFile.is_shared == True 
        ) 
        .first() 
    ) 
 
    if file is None: 
        raise HTTPException( 
            status_code=404, 
            detail="Shared file not found" 
        ) 
 
    path = Path(file.path) 
 
    if not path.exists(): 
        raise HTTPException( 
            status_code=404, 
            detail="Physical file not found" 
        ) 
 
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
 
    file_size = path.stat().st_size 
 
    range_header = request.headers.get("range") 
 
    # ===================================================== 
    # NO RANGE 
    # ===================================================== 
 
    if range_header is None: 
 
        def video_stream(): 
 
            with open(path, "rb") as buffer: 
 
                while True: 
 
                    chunk = buffer.read(CHUNK_SIZE) 
 
                    if not chunk: 
                        break 
 
                    yield chunk 
 
        return StreamingResponse( 
            video_stream(), 
            media_type=file.mime_type or "video/mp4", 
            headers={ 
                "Accept-Ranges": "bytes", 
                "Content-Length": str(file_size) 
            } 
        ) 
 
    # ===================================================== 
    # RANGE 
    # ===================================================== 
 
    try: 
 
        range_value = range_header.replace( 
            "bytes=", 
            "" 
        ) 
 
        start_str, end_str = range_value.split("-") 
 
        # Example: 
        # bytes=1000- 
        if start_str: 
 
            start = int(start_str) 
 
            if end_str: 
                end = int(end_str) 
            else: 
                end = file_size - 1 
 
        # Example: 
        # bytes=-500 
        else: 
 
            suffix_length = int(end_str) 
 
            if suffix_length <= 0: 
                raise ValueError 
 
            suffix_length = min( 
                suffix_length, 
                file_size 
            ) 
 
            start = file_size - suffix_length 
            end = file_size - 1 
 
    except (ValueError, AttributeError): 
 
        return StreamingResponse( 
            content=iter(()), 
            status_code=416, 
            headers={ 
                "Content-Range": f"bytes */{file_size}" 
            } 
        ) 
 
    # ===================================================== 
    # VALIDATE RANGE 
    # ===================================================== 
 
    if ( 
        start < 0 
        or start >= file_size 
        or end < start 
    ): 
 
        return StreamingResponse( 
            content=iter(()), 
            status_code=416, 
            headers={ 
                "Content-Range": f"bytes */{file_size}" 
            } 
        ) 
 
    end = min( 
        end, 
        file_size - 1 
    ) 
 
    content_length = ( 
        end - start + 1 
    ) 
 
    # ===================================================== 
    # STREAM RANGE 
    # ===================================================== 
 
    def range_video(): 
 
        with open(path, "rb") as buffer: 
 
            buffer.seek(start) 
 
            remaining = content_length 
 
            while remaining > 0: 
 
                chunk_size = min( 
                    CHUNK_SIZE, 
                    remaining 
                ) 
 
                chunk = buffer.read( 
                    chunk_size 
                ) 
 
                if not chunk: 
                    break 
 
                yield chunk 
 
                remaining -= len(chunk) 
 
    return StreamingResponse( 
        range_video(), 
        status_code=206, 
        media_type=file.mime_type or "video/mp4", 
        headers={ 
            "Content-Range": 
                f"bytes {start}-{end}/{file_size}", 
 
            "Accept-Ranges": 
                "bytes", 
 
            "Content-Length": 
                str(content_length) 
        } 
    ) 
 
 
# ========================================================= 
# PUBLIC FOLDER INFO 
# ========================================================= 
 
@sharing.get("/public/folder/{share_id}") 
def public_folder_info( 
    share_id: str, 
    db: Session = Depends(get_db) 
): 
 
    folder = ( 
        db.query(StorageFolder) 
        .filter( 
            StorageFolder.share_id == share_id, 
            StorageFolder.is_shared == True 
        ) 
        .first() 
    ) 
 
    if folder is None: 
        raise HTTPException( 
            status_code=404, 
            detail="Shared folder not found" 
        ) 
 
    child_folders = ( 
        db.query(StorageFolder) 
        .filter( 
            StorageFolder.parent_id == folder.id, 
            StorageFolder.user_id == folder.user_id 
        ) 
        .all() 
    ) 
 
    child_files = ( 
        db.query(StorageFile) 
        .filter( 
            StorageFile.folder_id == folder.id, 
            StorageFile.user_id == folder.user_id 
        ) 
        .all() 
    ) 
 
    return { 
        "folder": { 
            "id": folder.id, 
            "public_id": folder.public_id, 
            "name": folder.name 
        }, 
 
        "folders": [ 
            { 
                "id": child.id, 
                "public_id": child.public_id, 
                "name": child.name, 
                "type": "folder" 
            } 
            for child in child_folders 
        ], 
 
        "files": [ 
            { 
                "id": child.id, 
                "name": child.name, 
                "size": child.size, 
                "mime_type": child.mime_type, 
                "type": "file" 
            } 
            for child in child_files 
        ] 
    } 