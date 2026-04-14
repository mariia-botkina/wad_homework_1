from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    github_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
