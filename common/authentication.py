# common/authentication.py
import uuid

def generate_uuid():
    return str(uuid.uuid4())

def validate_uuid(input_uuid: str, admin_uuid: str) -> bool:
    return input_uuid == admin_uuid
