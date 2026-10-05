from fastapi import APIRouter,Depends,UploadFile,File
from fastapi.responses import StreamingResponse
from Controlls.security.SessionHandler import get_user
import shutil,os,uuid


r3=APIRouter(prefix="/upload",tags=["Upload file"])

@r3.post("/")
def upload(file:UploadFile=File(...),user=Depends(get_user),
           ):
    s="Assests/Videos/"
    os.makedirs("Assests/Videos/",exist_ok=True)
    ext=os.path.split(file.filename)[1]
    filename=f"{uuid.uuid4()}{ext}"
    path=os.path.join(s,filename)
    with open(path,"wb") as buffer:
        shutil.copyfileobj(file.file,buffer)


    

