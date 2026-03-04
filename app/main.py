from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User
from .auth import hash_pin, verify_pin

app = FastAPI(title="Formteile Fritsch Shopfloor API")

Base.metadata.create_all(bind=engine)


# DB Verbindung
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Shopfloor API läuft"}


# USER ERSTELLEN
@app.post("/users")
def create_user(name: str, role: str, pin: str, db: Session = Depends(get_db)):
    user = User(
        name=name,
        role=role,
        pin_hash=hash_pin(pin)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User erstellt", "user": name}


# LOGIN
@app.post("/login")
def login(pin: str, db: Session = Depends(get_db)):

    users = db.query(User).all()

    for user in users:
        if verify_pin(pin, user.pin_hash):
            return {
                "message": "Login erfolgreich",
                "user": user.name,
                "role": user.role
            }

    return {"message": "PIN falsch"}
