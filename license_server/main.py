# license_server/main.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from models import License
from database import get_engine, get_session, init_db
from sqlalchemy.orm import Session
from datetime import datetime
import json
import os
import threading
import time
from common.logging import setup_logging

# Setup logging
logger = setup_logging("license_server")

app = FastAPI()

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'license_server_config.json')
with open(CONFIG_PATH) as f:
    config = json.load(f)

engine = get_engine(CONFIG_PATH)
init_db(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Pydantic Models
class ValidateRequest(BaseModel):
    key: str

class ValidateResponse(BaseModel):
    valid: bool
    scrapers: list

class CreateLicenseRequest(BaseModel):
    key: str
    valid_until: str  # ISO format date
    scrapers: list  # List of scraper names or ["all"]
    usage_per_month: int

class DeleteLicenseRequest(BaseModel):
    key: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Endpoints
@app.post("/validate", response_model=ValidateResponse)
def validate_license(request: ValidateRequest, db: Session = Depends(get_db)):
    license = db.query(License).filter(License.key == request.key).first()
    if not license:
        logger.warning(f"Validation failed: Invalid key {request.key}")
        raise HTTPException(status_code=400, detail="Invalid license key")
    if license.valid_until < datetime.utcnow().date():
        logger.warning(f"Validation failed: License {request.key} expired")
        raise HTTPException(status_code=400, detail="License expired")
    if license.usage_count >= license.usage_per_month:
        logger.warning(f"Validation failed: License {request.key} usage limit reached")
        raise HTTPException(status_code=400, detail="License usage limit reached")
    # Update usage
    license.usage_count += 1
    db.commit()
    scrapers = license.scrapers.split(",")
    logger.info(f"License {request.key} validated successfully")
    return ValidateResponse(valid=True, scrapers=scrapers)

@app.post("/create_license")
def create_license(request: CreateLicenseRequest, db: Session = Depends(get_db)):
    existing_license = db.query(License).filter(License.key == request.key).first()
    if existing_license:
        logger.warning(f"Creation failed: License key {request.key} already exists")
        raise HTTPException(status_code=400, detail="License key already exists")
    try:
        valid_until_date = datetime.fromisoformat(request.valid_until).date()
    except ValueError:
        logger.error(f"Creation failed: Invalid date format for license {request.key}")
        raise HTTPException(status_code=400, detail="Invalid date format")
    scrapers = ",".join(request.scrapers)
    new_license = License(
        key=request.key,
        valid_until=valid_until_date,
        scrapers=scrapers,
        usage_per_month=request.usage_per_month,
        usage_count=0
    )
    db.add(new_license)
    db.commit()
    logger.info(f"License {request.key} created successfully")
    return {"status": "License created"}

@app.post("/delete_license")
def delete_license(request: DeleteLicenseRequest, db: Session = Depends(get_db)):
    license = db.query(License).filter(License.key == request.key).first()
    if not license:
        logger.warning(f"Deletion failed: License key {request.key} not found")
        raise HTTPException(status_code=404, detail="License key not found")
    db.delete(license)
    db.commit()
    logger.info(f"License {request.key} deleted successfully")
    return {"status": "License deleted"}

@app.get("/list_licenses")
def list_licenses(db: Session = Depends(get_db)):
    licenses = db.query(License).all()
    result = []
    for license in licenses:
        result.append({
            "key": license.key,
            "valid_until": license.valid_until.isoformat(),
            "scrapers": license.scrapers.split(","),
            "usage_per_month": license.usage_per_month,
            "usage_count": license.usage_count
        })
    logger.info("List licenses requested")
    return {"licenses": result}

# Background Task to Reset Monthly Usage
def reset_monthly_usage():
    while True:
        now = datetime.utcnow()
        # Calculate next reset time (first day of next month at 00:00 UTC)
        if now.month == 12:
            next_reset = datetime(year=now.year + 1, month=1, day=1)
        else:
            next_reset = datetime(year=now.year, month=now.month + 1, day=1)
        delta_seconds = (next_reset - now).total_seconds()
        logger.info(f"Next monthly usage reset in {delta_seconds} seconds")
        time.sleep(delta_seconds)
        # Reset usage_count
        with SessionLocal() as db:
            db.query(License).update({License.usage_count: 0})
            db.commit()
            logger.info("Monthly usage counts reset")

# Start background thread
reset_thread = threading.Thread(target=reset_monthly_usage, daemon=True)
reset_thread.start()

if __name__ == "__main__":
    import uvicorn
    from sqlalchemy.orm import sessionmaker
    uvicorn.run(app, host=config["license_server"]["ip"], port=config["license_server"]["port"])
