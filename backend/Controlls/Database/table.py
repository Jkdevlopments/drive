from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey,BigInteger,Boolean
from sqlalchemy.orm import relationship
from .init import Base
import uuid
from datetime import datetime,timezone,timedelta


class Auditlog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    username = Column(String, nullable=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)

    method = Column(String, nullable=True)
    path = Column(String, nullable=True)

    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    details = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = relationship(
        "Users",
        back_populates="audit_logs"
    )


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    email = Column(String, unique=True)
    password = Column(String)

    audit_logs = relationship(
        "Auditlog",
        back_populates="user"
    )


class StorageFolder(Base):
    __tablename__="storage_folders"
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(
    String(36),
    unique=True,
    nullable=False,
    default=lambda: str(uuid.uuid4())
)
    name = Column(String(255), nullable=False)
    parent_id=Column(Integer,ForeignKey("storage_folders.id"),nullable=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    parent=relationship(
        "StorageFolder",
        remote_side=[id]
    )

    share_id = Column(
        String(36),
        unique=True,
        nullable=True,
        index=True
    )

    is_shared = Column(
        Boolean,
        default=False,
        nullable=False
    )

    share_permission = Column(
        String(20),
        default="viewer",
        nullable=False
    )





# உங்கள் existing Base-ஐ இங்கே பயன்படுத்தவும்
# from Controlls.Database.init import Base


class StorageFile(Base):
    __tablename__ = "storage_files"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(255),
        nullable=False
    )

    stored_name = Column(
        String(255),
        nullable=False
    )

    path = Column(
        String(1000),
        nullable=False
    )

    mime_type = Column(
        String(255),
        nullable=True
    )

    size = Column(
        BigInteger,
        nullable=False,
        default=0
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    folder_id = Column(
        Integer,
        ForeignKey("storage_folders.id"),
        nullable=True,
        index=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    share_id = Column(
    String(36),
    unique=True,
    nullable=True,
    index=True
)

    is_shared = Column(
    Boolean,
    default=False,
    nullable=False
)

    share_permission = Column(
    String(20),
    default="viewer",
    nullable=False
)

