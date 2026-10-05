from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File
)

from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from Controlls.security.SessionHandler import get_user
from Controlls.Database.init import get_db
from Controlls.Database.table import (
    Users,
    StorageFolder,
    StorageFile
)

from Controlls.schemas import (
    CreateFolderRequest,
    FolderResponse,
    RenameRequest,
    MoveRequest
)


# =========================================================
# ROUTER
# =========================================================

storage = APIRouter(
    prefix="/storage",
    tags=["Storage"]
)


# =========================================================
# STORAGE ROOT
# =========================================================

STORAGE_ROOT = Path("Storage")

STORAGE_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# SETTINGS
# =========================================================

MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024

CHUNK_SIZE = 1024 * 1024


# =========================================================
# GET DATABASE USER
# =========================================================

def get_current_user(
    auth_user,
    db: Session
):

    username, email = auth_user

    user = (
        db.query(Users)
        .filter(
            Users.email == email
        )
        .first()
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


# =========================================================
# VALIDATE NAME
# =========================================================

def validate_name(name: str):

    name = name.strip()

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty"
        )

    if name in [".", ".."]:

        raise HTTPException(
            status_code=400,
            detail="Invalid name"
        )

    if "/" in name or "\\" in name:

        raise HTTPException(
            status_code=400,
            detail="Invalid name"
        )

    return name


# =========================================================
# USER STORAGE ROOT
# =========================================================

def get_user_root(
    user_id: int
):

    root = (
        STORAGE_ROOT /
        str(user_id)
    )

    root.mkdir(
        parents=True,
        exist_ok=True
    )

    return root


# =========================================================
# GET FOLDER BY INTERNAL ID
# =========================================================

def get_user_folder(
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
# GET FOLDER BY PUBLIC UUID
# =========================================================

def get_user_folder_by_public_id(
    public_id: str,
    user_id: int,
    db: Session
):

    folder = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.public_id == public_id,
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
# RESOLVE FOLDER
#
# Supports:
#
# 25
#
# OR
#
# 6ac26ff3-73bc-83ee-b3f3-1efc4e0d52af
#
# =========================================================

def resolve_folder(
    folder_reference: str | None,
    user_id: int,
    db: Session
):

    if folder_reference is None:

        return None

    folder_reference = folder_reference.strip()

    if not folder_reference:

        return None

    # -----------------------------------------------------
    # First try public UUID
    # -----------------------------------------------------

    folder = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.public_id == folder_reference,
            StorageFolder.user_id == user_id
        )
        .first()
    )

    if folder is not None:

        return folder

    # -----------------------------------------------------
    # Backward compatibility with old numeric IDs
    # -----------------------------------------------------

    if folder_reference.isdigit():

        folder = get_user_folder(
            int(folder_reference),
            user_id,
            db
        )

        return folder

    # -----------------------------------------------------
    # Invalid / unauthorized
    # -----------------------------------------------------

    raise HTTPException(
        status_code=404,
        detail="Folder not found"
    )


# =========================================================
# BUILD FOLDER PHYSICAL PATH
# =========================================================

def get_folder_path(
    user_root: Path,
    folder: StorageFolder,
    db: Session,
    user_id: int
):

    parts = []

    current = folder

    while current is not None:

        parts.insert(
            0,
            current.name
        )

        if current.parent_id is None:

            break

        current = (
            db.query(StorageFolder)
            .filter(
                StorageFolder.id == current.parent_id,
                StorageFolder.user_id == user_id
            )
            .first()
        )

        if current is None:

            raise HTTPException(
                status_code=404,
                detail="Invalid folder hierarchy"
            )

    folder_path = user_root

    for part in parts:

        folder_path = (
            folder_path /
            part
        )

    return folder_path


# =========================================================
# GET FILE
# =========================================================

def get_user_file(
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


# =========================================================
# CREATE FOLDER
#
# POST /storage/folder
# =========================================================

@storage.post(
    "/folder",
    response_model=FolderResponse,
    status_code=201
)
def create_folder(
    data: CreateFolderRequest,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    folder_name = validate_name(
        data.name
    )

    user_root = get_user_root(
        user.id
    )

    # =====================================================
    # FIND PARENT
    # =====================================================

    parent = None

    if data.parent_id is not None:

        parent = get_user_folder(
            data.parent_id,
            user.id,
            db
        )

    # =====================================================
    # DUPLICATE CHECK
    # =====================================================

    existing = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.user_id == user.id,
            StorageFolder.parent_id == data.parent_id,
            StorageFolder.name == folder_name
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Folder already exists"
        )

    # =====================================================
    # BUILD PHYSICAL PATH
    # =====================================================

    if parent is None:

        folder_path = (
            user_root /
            folder_name
        )

    else:

        parent_path = get_folder_path(
            user_root,
            parent,
            db,
            user.id
        )

        folder_path = (
            parent_path /
            folder_name
        )

    # =====================================================
    # PHYSICAL DUPLICATE
    # =====================================================

    if folder_path.exists():

        raise HTTPException(
            status_code=409,
            detail="Folder already exists on server"
        )

    # =====================================================
    # CREATE PHYSICAL FOLDER
    # =====================================================

    try:

        folder_path.mkdir(
            parents=True,
            exist_ok=False
        )

    except OSError as error:

        print(
            "Folder creation error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to create folder"
        )

    # =====================================================
    # DATABASE
    # =====================================================

    try:

        new_folder = StorageFolder(
            name=folder_name,
            parent_id=data.parent_id,
            user_id=user.id
        )

        db.add(
            new_folder
        )

        db.commit()

        db.refresh(
            new_folder
        )

        return new_folder

    except Exception as error:

        db.rollback()

        try:

            folder_path.rmdir()

        except OSError:

            pass

        print(
            "Database folder error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to save folder"
        )


# =========================================================
# GET ALL FOLDERS
#
# GET /storage/folders
# =========================================================

@storage.get("/folders")
def get_folders(
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    folders = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.user_id == user.id
        )
        .all()
    )

    return [

        {
            "id": folder.id,

            "public_id":
                folder.public_id,

            "name":
                folder.name,

            "parent_id":
                folder.parent_id,

            "type":
                "folder"
        }

        for folder in folders

    ]


# =========================================================
# GET CONTENTS
#
# Existing:
#
# GET /storage/contents
#
# GET /storage/contents?folder_id=25
#
# New:
#
# GET /storage/contents?folder_id=UUID
#
# Both work.
# =========================================================

@storage.get("/contents")
def get_contents(
    folder_id: str | None = None,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    # =====================================================
    # RESOLVE FOLDER
    # =====================================================

    current_folder = resolve_folder(
        folder_id,
        user.id,
        db
    )

    internal_folder_id = (
        current_folder.id
        if current_folder is not None
        else None
    )

    # =====================================================
    # CHILD FOLDERS
    # =====================================================

    folders = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.user_id == user.id,
            StorageFolder.parent_id == internal_folder_id
        )
        .all()
    )

    # =====================================================
    # CHILD FILES
    # =====================================================

    files = (
        db.query(StorageFile)
        .filter(
            StorageFile.user_id == user.id,
            StorageFile.folder_id == internal_folder_id
        )
        .all()
    )

    # =====================================================
    # FOLDER RESPONSE
    # =====================================================

    folder_data = []

    for folder in folders:

        folder_data.append({

            "id":
                folder.id,

            "public_id":
                folder.public_id,

            "name":
                folder.name,

            "parent_id":
                folder.parent_id,

            "type":
                "folder",

            "modified":
                (
                    folder.updated_at.isoformat()
                    if getattr(
                        folder,
                        "updated_at",
                        None
                    )
                    else "Just now"
                )

        })

    # =====================================================
    # FILE RESPONSE
    # =====================================================

    file_data = []

    for file in files:

        file_data.append({

            "id":
                file.id,

            "name":
                file.name,

            "folder_id":
                file.folder_id,

            "size":
                file.size or 0,

            "mime_type":
                file.mime_type,

            "type":
                "file",

            "modified":
                (
                    file.updated_at.isoformat()
                    if getattr(
                        file,
                        "updated_at",
                        None
                    )
                    else "Just now"
                )

        })

    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "folder_id":
            internal_folder_id,

        "folder_public_id":
            (
                current_folder.public_id
                if current_folder
                else None
            ),

        "folder_name":
            (
                current_folder.name
                if current_folder
                else None
            ),

        "folders":
            folder_data,

        "files":
            file_data

    }


# =========================================================
# GET FOLDER BY PUBLIC URL
#
# GET /storage/folders/{public_id}
#
# Example:
#
# /storage/folders/
# 6ac26ff3-73bc-83ee-b3f3-1efc4e0d52af
#
# =========================================================

@storage.get("/folders/{public_id}")
def get_folder_by_public_url(
    public_id: str,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    # =====================================================
    # OWNERSHIP CHECK
    # =====================================================

    folder = get_user_folder_by_public_id(
        public_id,
        user.id,
        db
    )

    # =====================================================
    # CHILD FOLDERS
    # =====================================================

    folders = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.user_id == user.id,
            StorageFolder.parent_id == folder.id
        )
        .all()
    )

    # =====================================================
    # CHILD FILES
    # =====================================================

    files = (
        db.query(StorageFile)
        .filter(
            StorageFile.user_id == user.id,
            StorageFile.folder_id == folder.id
        )
        .all()
    )

    # =====================================================
    # FOLDER DATA
    # =====================================================

    folder_data = [

        {
            "id":
                item.id,

            "public_id":
                item.public_id,

            "name":
                item.name,

            "parent_id":
                item.parent_id,

            "type":
                "folder",

            "modified":
                (
                    item.updated_at.isoformat()
                    if getattr(
                        item,
                        "updated_at",
                        None
                    )
                    else "Just now"
                )
        }

        for item in folders

    ]

    # =====================================================
    # FILE DATA
    # =====================================================

    file_data = [

        {
            "id":
                item.id,

            "name":
                item.name,

            "folder_id":
                item.folder_id,

            "size":
                item.size or 0,

            "mime_type":
                item.mime_type,

            "type":
                "file",

            "modified":
                (
                    item.updated_at.isoformat()
                    if getattr(
                        item,
                        "updated_at",
                        None
                    )
                    else "Just now"
                )
        }

        for item in files

    ]

    return {

        "folder": {

            "id":
                folder.id,

            "public_id":
                folder.public_id,

            "name":
                folder.name,

            "parent_id":
                folder.parent_id

        },

        "folders":
            folder_data,

        "files":
            file_data

    }


# =========================================================
# UPLOAD FILE
#
# POST /storage/upload
# =========================================================

@storage.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: int | None = None,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    # =====================================================
    # TARGET FOLDER
    # =====================================================

    folder = None

    if folder_id is not None:

        folder = get_user_folder(
            folder_id,
            user.id,
            db
        )

    # =====================================================
    # FILE NAME
    # =====================================================

    original_name = Path(
        file.filename or "file"
    ).name

    original_name = validate_name(
        original_name
    )

    # =====================================================
    # DESTINATION
    # =====================================================

    user_root = get_user_root(
        user.id
    )

    if folder is None:

        destination = user_root

    else:

        destination = get_folder_path(
            user_root,
            folder,
            db,
            user.id
        )

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    # =====================================================
    # DUPLICATE
    # =====================================================

    existing = (
        db.query(StorageFile)
        .filter(
            StorageFile.user_id == user.id,
            StorageFile.folder_id == folder_id,
            StorageFile.name == original_name
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail="File already exists"
        )

    # =====================================================
    # RANDOM PHYSICAL NAME
    # =====================================================

    extension = Path(
        original_name
    ).suffix

    stored_name = (
        f"{uuid4().hex}{extension}"
    )

    physical_path = (
        destination /
        stored_name
    )

    # =====================================================
    # SAVE FILE
    # =====================================================

    total_size = 0

    try:

        with open(
            physical_path,
            "wb"
        ) as output:

            while True:

                chunk = await file.read(
                    CHUNK_SIZE
                )

                if not chunk:
                    break

                total_size += len(
                    chunk
                )

                if total_size > MAX_FILE_SIZE:

                    try:
                        physical_path.unlink()
                    except OSError:
                        pass

                    raise HTTPException(
                        status_code=413,
                        detail="File too large"
                    )

                output.write(
                    chunk
                )

    except HTTPException:

        raise

    except Exception as error:

        print(
            "Upload error:",
            error
        )

        try:
            physical_path.unlink()
        except OSError:
            pass

        raise HTTPException(
            status_code=500,
            detail="Failed to upload file"
        )

    # =====================================================
    # DATABASE
    # =====================================================

    try:

        new_file = StorageFile(
            name=original_name,
            stored_name=stored_name,
            path=str(physical_path),
            mime_type=file.content_type,
            size=total_size,
            user_id=user.id,
            folder_id=folder_id
        )

        db.add(
            new_file
        )

        db.commit()

        db.refresh(
            new_file
        )

    except Exception as error:

        db.rollback()

        try:
            physical_path.unlink()
        except OSError:
            pass

        print(
            "File DB error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to save file information"
        )

    return {

        "message":
            "File uploaded successfully",

        "id":
            new_file.id,

        "name":
            new_file.name,

        "folder_id":
            new_file.folder_id,

        "size":
            new_file.size,

        "mime_type":
            new_file.mime_type

    }


# =========================================================
# DOWNLOAD FILE
# =========================================================

@storage.get(
    "/file/{file_id}/download"
)
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    file = get_user_file(
        file_id,
        user.id,
        db
    )

    physical_path = Path(
        file.path
    )

    if not physical_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Physical file not found"
        )

    return FileResponse(
        path=physical_path,
        filename=file.name,
        media_type=(
            file.mime_type
            or "application/octet-stream"
        )
    )


# =========================================================
# OPEN FILE
# =========================================================

@storage.get(
    "/file/{file_id}/open"
)
def open_file(
    file_id: int,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    file = get_user_file(
        file_id,
        user.id,
        db
    )

    physical_path = Path(
        file.path
    )

    if not physical_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Physical file not found"
        )

    return FileResponse(
        path=physical_path,
        media_type=(
            file.mime_type
            or "application/octet-stream"
        )
    )


# =========================================================
# RENAME FILE
# =========================================================

@storage.patch(
    "/file/{file_id}"
)
def rename_file(
    file_id: int,
    data: RenameRequest,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    file = get_user_file(
        file_id,
        user.id,
        db
    )

    new_name = validate_name(
        data.name
    )

    duplicate = (
        db.query(StorageFile)
        .filter(
            StorageFile.user_id == user.id,
            StorageFile.folder_id == file.folder_id,
            StorageFile.name == new_name,
            StorageFile.id != file.id
        )
        .first()
    )

    if duplicate:

        raise HTTPException(
            status_code=409,
            detail="File already exists"
        )

    file.name = new_name

    db.commit()

    db.refresh(
        file
    )

    return {

        "message":
            "File renamed",

        "id":
            file.id,

        "name":
            file.name

    }


# =========================================================
# DELETE FILE
# =========================================================

@storage.delete(
    "/file/{file_id}"
)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    file = get_user_file(
        file_id,
        user.id,
        db
    )

    physical_path = Path(
        file.path
    )

    try:

        if physical_path.exists():

            physical_path.unlink()

        db.delete(
            file
        )

        db.commit()

    except Exception as error:

        db.rollback()

        print(
            "Delete file error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to delete file"
        )

    return {
        "message": "File deleted",
        "id": file_id
    }


# =========================================================
# DELETE FOLDER - RECURSIVE
# =========================================================

@storage.delete(
    "/folder/{folder_id}"
)
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    # =====================================================
    # MAIN FOLDER
    # =====================================================

    folder = get_user_folder(
        folder_id,
        user.id,
        db
    )

    user_root = get_user_root(
        user.id
    )

    folder_path = get_folder_path(
        user_root,
        folder,
        db,
        user.id
    )

    # =====================================================
    # SAFETY
    # =====================================================

    if folder_path == user_root:

        raise HTTPException(
            status_code=400,
            detail="Cannot delete storage root"
        )

    # =====================================================
    # GET ALL CHILD FOLDERS
    # =====================================================

    def get_all_child_folder_ids(
        parent_id: int
    ):

        result = []

        children = (
            db.query(StorageFolder)
            .filter(
                StorageFolder.parent_id == parent_id,
                StorageFolder.user_id == user.id
            )
            .all()
        )

        for child in children:

            result.extend(
                get_all_child_folder_ids(
                    child.id
                )
            )

            result.append(
                child.id
            )

        return result

    child_folder_ids = (
        get_all_child_folder_ids(
            folder.id
        )
    )

    all_folder_ids = [
        folder.id
    ] + child_folder_ids

    # =====================================================
    # DELETE PHYSICAL DIRECTORY
    # =====================================================

    if folder_path.exists():

        if not folder_path.is_dir():

            raise HTTPException(
                status_code=400,
                detail="Invalid folder path"
            )

        try:

            import shutil

            shutil.rmtree(
                folder_path
            )

        except Exception as error:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to delete physical folder: "
                    f"{str(error)}"
                )
            )

    # =====================================================
    # DELETE FILE RECORDS
    # =====================================================

    (
        db.query(StorageFile)
        .filter(
            StorageFile.user_id == user.id,
            StorageFile.folder_id.in_(
                all_folder_ids
            )
        )
        .delete(
            synchronize_session=False
        )
    )

    # =====================================================
    # DELETE CHILD FOLDERS
    # =====================================================

    for child_id in child_folder_ids:

        child_folder = (
            db.query(StorageFolder)
            .filter(
                StorageFolder.id == child_id,
                StorageFolder.user_id == user.id
            )
            .first()
        )

        if child_folder:

            db.delete(
                child_folder
            )

    # =====================================================
    # DELETE MAIN FOLDER
    # =====================================================

    db.delete(
        folder
    )

    # =====================================================
    # COMMIT
    # =====================================================

    db.commit()

    return {

        "message":
            "Folder and all contents deleted successfully",

        "folder_id":
            folder_id

    }


# =========================================================
# RENAME FOLDER
# =========================================================

@storage.patch(
    "/folder/{folder_id}"
)
def rename_folder(
    folder_id: int,
    data: RenameRequest,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    folder = get_user_folder(
        folder_id,
        user.id,
        db
    )

    new_name = validate_name(
        data.name
    )

    # =====================================================
    # DUPLICATE
    # =====================================================

    duplicate = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.user_id == user.id,
            StorageFolder.parent_id == folder.parent_id,
            StorageFolder.name == new_name,
            StorageFolder.id != folder.id
        )
        .first()
    )

    if duplicate:

        raise HTTPException(
            status_code=409,
            detail="Folder already exists"
        )

    # =====================================================
    # PHYSICAL PATH
    # =====================================================

    user_root = get_user_root(
        user.id
    )

    old_path = get_folder_path(
        user_root,
        folder,
        db,
        user.id
    )

    new_path = (
        old_path.parent /
        new_name
    )

    if new_path.exists():

        raise HTTPException(
            status_code=409,
            detail="Folder already exists on server"
        )

    try:

        old_path.rename(
            new_path
        )

    except OSError as error:

        print(
            "Rename folder error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to rename folder"
        )

    old_name = folder.name

    folder.name = new_name

    try:

        db.commit()

        db.refresh(
            folder
        )

    except Exception:

        db.rollback()

        try:

            new_path.rename(
                old_path
            )

        except OSError:

            pass

        folder.name = old_name

        raise HTTPException(
            status_code=500,
            detail="Failed to update folder"
        )

    return {

        "message":
            "Folder renamed",

        "id":
            folder.id,

        "public_id":
            folder.public_id,

        "name":
            folder.name

    }


# =========================================================
# MOVE FILE
# =========================================================

@storage.patch(
    "/file/{file_id}/move"
)
def move_file(
    file_id: int,
    data: MoveRequest,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    file = get_user_file(
        file_id,
        user.id,
        db
    )

    # =====================================================
    # TARGET FOLDER
    # =====================================================

    target_folder = None

    if data.folder_id is not None:

        target_folder = get_user_folder(
            data.folder_id,
            user.id,
            db
        )

    # =====================================================
    # DUPLICATE
    # =====================================================

    duplicate = (
        db.query(StorageFile)
        .filter(
            StorageFile.user_id == user.id,
            StorageFile.folder_id == data.folder_id,
            StorageFile.name == file.name,
            StorageFile.id != file.id
        )
        .first()
    )

    if duplicate:

        raise HTTPException(
            status_code=409,
            detail="File already exists in target folder"
        )

    # =====================================================
    # TARGET PATH
    # =====================================================

    user_root = get_user_root(
        user.id
    )

    if target_folder is None:

        target_path = user_root

    else:

        target_path = get_folder_path(
            user_root,
            target_folder,
            db,
            user.id
        )

    target_path.mkdir(
        parents=True,
        exist_ok=True
    )

    old_path = Path(
        file.path
    )

    new_path = (
        target_path /
        file.stored_name
    )

    try:

        old_path.rename(
            new_path
        )

        file.folder_id = (
            data.folder_id
        )

        file.path = str(
            new_path
        )

        db.commit()

        db.refresh(
            file
        )

    except Exception as error:

        db.rollback()

        print(
            "Move file error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to move file"
        )

    return {

        "message":
            "File moved",

        "id":
            file.id,

        "folder_id":
            file.folder_id

    }


# =========================================================
# MOVE FOLDER
# =========================================================

@storage.patch(
    "/folder/{folder_id}/move"
)
def move_folder(
    folder_id: int,
    data: MoveRequest,
    db: Session = Depends(get_db),
    auth_user=Depends(get_user)
):

    user = get_current_user(
        auth_user,
        db
    )

    folder = get_user_folder(
        folder_id,
        user.id,
        db
    )

    # =====================================================
    # CANNOT MOVE INTO ITSELF
    # =====================================================

    if data.folder_id == folder.id:

        raise HTTPException(
            status_code=400,
            detail="Cannot move folder into itself"
        )

    # =====================================================
    # TARGET
    # =====================================================

    target_folder = None

    if data.folder_id is not None:

        target_folder = get_user_folder(
            data.folder_id,
            user.id,
            db
        )

        # =================================================
        # PREVENT MOVING INTO CHILD
        # =================================================

        current = target_folder

        while current is not None:

            if current.id == folder.id:

                raise HTTPException(
                    status_code=400,
                    detail="Cannot move folder into its child"
                )

            if current.parent_id is None:

                break

            current = (
                db.query(StorageFolder)
                .filter(
                    StorageFolder.id == current.parent_id,
                    StorageFolder.user_id == user.id
                )
                .first()
            )

    # =====================================================
    # DUPLICATE
    # =====================================================

    duplicate = (
        db.query(StorageFolder)
        .filter(
            StorageFolder.user_id == user.id,
            StorageFolder.parent_id == data.folder_id,
            StorageFolder.name == folder.name,
            StorageFolder.id != folder.id
        )
        .first()
    )

    if duplicate:

        raise HTTPException(
            status_code=409,
            detail="Folder already exists in target folder"
        )

    # =====================================================
    # OLD PATH
    # =====================================================

    user_root = get_user_root(
        user.id
    )

    old_path = get_folder_path(
        user_root,
        folder,
        db,
        user.id
    )

    # =====================================================
    # TARGET PATH
    # =====================================================

    if target_folder is None:

        target_path = user_root

    else:

        target_path = get_folder_path(
            user_root,
            target_folder,
            db,
            user.id
        )

    new_path = (
        target_path /
        folder.name
    )

    if new_path.exists():

        raise HTTPException(
            status_code=409,
            detail="Target folder already exists"
        )

    # =====================================================
    # MOVE
    # =====================================================

    try:

        old_path.rename(
            new_path
        )

        folder.parent_id = (
            data.folder_id
        )

        db.commit()

        db.refresh(
            folder
        )

    except Exception as error:

        db.rollback()

        print(
            "Move folder error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to move folder"
        )

    return {

        "message":
            "Folder moved",

        "id":
            folder.id,

        "public_id":
            folder.public_id,

        "parent_id":
            folder.parent_id

    }