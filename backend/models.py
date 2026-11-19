from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String
from database import Base

class TelecomSiteModel(Base):
    __tablename__ = "telecom_sites"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_id = Column(String(50), unique=True, index=True, nullable=False)
    site_name = Column(String(255), nullable=False)
    region = Column(String(100), nullable=True)
    wilaya = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    source_kmz = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
