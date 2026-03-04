from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pin(pin: str):
    return pwd_context.hash(pin)

def verify_pin(pin: str, pin_hash: str):
    return pwd_context.verify(pin, pin_hash)
