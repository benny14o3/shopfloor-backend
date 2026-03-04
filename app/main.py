from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User
from .auth import hash_pin, verify_pin
from .models import User, Article
from .models import Process
from .models import Characteristic

app = FastAPI(title="Formteile Fritsch Shopfloor API")


@app.on_event("startup")
def startup():
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

# ARTIKEL ERSTELLEN
@app.post("/articles")
def create_article(
    artikelnummer: str,
    bezeichnung: str,
    material: str,
    werkzeug: str,
    kavitaeten: int,
    revision: str,
    db: Session = Depends(get_db)
):

    article = Article(
        artikelnummer=artikelnummer,
        bezeichnung=bezeichnung,
        material=material,
        werkzeug=werkzeug,
        kavitaeten=kavitaeten,
        revision=revision
    )

    db.add(article)
    db.commit()
    db.refresh(article)

    return {"message": "Artikel erstellt", "artikelnummer": artikelnummer}

# ALLE ARTIKEL
@app.get("/articles")
def get_articles(db: Session = Depends(get_db)):
    articles = db.query(Article).all()
    return articles

# PROZESS
@app.post("/processes")
def create_process(
    article_id: str,
    nummer: int,
    name: str,
    maschine: str,
    db: Session = Depends(get_db)
):

    process = Process(
        article_id=article_id,
        nummer=nummer,
        name=name,
        maschine=maschine
    )

    db.add(process)
    db.commit()
    db.refresh(process)

    return {"message": "Prozess erstellt"}

@app.get("/processes/{article_id}")
def get_processes(article_id: str, db: Session = Depends(get_db)):

    processes = db.query(Process).filter(Process.article_id == article_id).all()

    return processes

# PRÜFMERKMAL
@app.post("/characteristics")
def create_characteristic(
    process_id: str,
    name: str,
    sollwert: str,
    tol_plus: str,
    tol_minus: str,
    messmittel: str,
    frequenz: str,
    db: Session = Depends(get_db)
):

    characteristic = Characteristic(
        process_id=process_id,
        name=name,
        sollwert=sollwert,
        tol_plus=tol_plus,
        tol_minus=tol_minus,
        messmittel=messmittel,
        frequenz=frequenz
    )

    db.add(characteristic)
    db.commit()
    db.refresh(characteristic)

    return {"message": "Prüfmerkmal erstellt"}

@app.get("/characteristics/{process_id}")
def get_characteristics(process_id: str, db: Session = Depends(get_db)):

    characteristics = db.query(Characteristic).filter(
        Characteristic.process_id == process_id
    ).all()

    return characteristics

