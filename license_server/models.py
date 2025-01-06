# license_server/models.py
from sqlalchemy import Column, String, Integer, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class License(Base):
    __tablename__ = 'licenses'

    key = Column(String, primary_key=True, index=True)
    valid_until = Column(Date, nullable=False)
    scrapers = Column(String, nullable=False)  # Comma-separated scraper names or "all"
    usage_per_month = Column(Integer, nullable=False)
    usage_count = Column(Integer, default=0)
