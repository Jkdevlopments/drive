from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from router import Register,Login,Upload,Logout,Stream,Storage,Sharing
from Controlls.Database.init import Base,engine
from Controlls.Database.init import session_loacl
from Controlls.Database.table import Auditlog
from Controlls.security.SessionHandler import refresh
from Controlls.security.SessionHandler import r10
from Controlls.security.csrf import r11

from Controlls.security.csrf import middle

from time import perf_counter

Base.metadata.create_all(bind=engine)

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bicollateral-unmarred-vinita.ngrok-free.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]

)
app.include_router(Register.r1)
app.include_router(Login.r2)
app.include_router(Upload.r3)
app.include_router(refresh)
app.include_router(Stream.stream)
app.include_router(Logout.logou)
app.include_router(Storage.storage)
app.include_router(Sharing.sharing)
app.include_router(r10)
app.include_router(r11)
app.add_middleware(middle)



@app.middleware("http")
async def middleware(request:Request,call_next):
    start=perf_counter()
    response=None
    error=None
    try:
        response=await call_next(request)
        return response
    except Exception as e:
        error=str(e)
        raise
    finally:
        process_time=perf_counter()-start
        user_id=getattr(request.state,"user_id",None)
        user_name=getattr(request.state,"user_name",None)

        client_ip=None
        if request.client:
            client_ip=request.client.host
        user_agent=request.headers.get("user-agent")
        if response is not None:
            status_code=response.status_code

        else:
            status_code=500

        if 200 <= status_code < 400:
            status = "SUCCESS"
        else:
            status = "FAILED"
        db=session_loacl()
        try:

            log = Auditlog(
                user_id=user_id,
                username=user_name,
                action="REQUEST",
                status=status,
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                user_agent=user_agent,
                details=f"status={status_code}, time={process_time:.4f}s"
            )

            db.add(log)
            db.commit()

        except Exception as log_error:

            db.rollback()
            print("Audit log error:", log_error)

        finally:

            db.close()







