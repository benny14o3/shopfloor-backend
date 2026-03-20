from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from .database import engine, Base, SessionLocal
from .models import User, Article, Process, Characteristic, Measurement, Batch, Machine
from .auth import hash_pin, verify_pin
from .spc import calculate_spc

app = FastAPI(title="Formteile Fritsch Shopfloor API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# STARTUP
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Maschinen initial anlegen
    if db.query(Machine).count() == 0:
        machines = [
            Machine(machine_id="MAPLAN GUMMI-01", status="running"),
            Machine(machine_id="MAPLAN-GUMMI-02", status="stopped"),
            Machine(machine_id="MAPLAN-SILIKON-03", status="setup"),
            Machine(machine_id="MAPLAN-SILIKON-04", status="setup"),
        ]
        db.add_all(machines)
        db.commit()

    db.close()


# DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Shopfloor API läuft"}


# USER
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


# ARTIKEL
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


@app.get("/articles")
def get_articles(db: Session = Depends(get_db)):
    return db.query(Article).all()


# PROZESSE
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
    return db.query(Process).filter(Process.article_id == article_id).all()


# PRÜFMERKMALE
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
    return db.query(Characteristic).filter(
        Characteristic.process_id == process_id
    ).all()


# MESSWERTE
@app.post("/measurements")
def create_measurement(
    characteristic_id: str,
    value: str,
    db: Session = Depends(get_db)
):
    measurement = Measurement(
        characteristic_id=characteristic_id,
        value=value,
        timestamp=str(datetime.utcnow())
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return {"message": "Messwert gespeichert"}


@app.get("/measurements/{characteristic_id}")
def get_measurements(characteristic_id: str, db: Session = Depends(get_db)):
    return db.query(Measurement).filter(
        Measurement.characteristic_id == characteristic_id
    ).all()


# BATCHES
@app.post("/batches")
def create_batch(
    article_id: str,
    chargennummer: str,
    maschine: str,
    operator: str,
    materialcharge: str,
    db: Session = Depends(get_db)
):
    batch = Batch(
        article_id=article_id,
        chargennummer=chargennummer,
        maschine=maschine,
        operator=operator,
        materialcharge=materialcharge,
        start_time=str(datetime.utcnow())
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@app.get("/batches/{article_id}")
def get_batches(article_id: str, db: Session = Depends(get_db)):
    return db.query(Batch).filter(
        Batch.article_id == article_id
    ).all()


# SPC
@app.get("/spc/{characteristic_id}")
def calculate_spc_for_characteristic(
    characteristic_id: str,
    db: Session = Depends(get_db)
):
    characteristic = db.query(Characteristic).filter(
        Characteristic.id == characteristic_id
    ).first()

    measurements = db.query(Measurement).filter(
        Measurement.characteristic_id == characteristic_id
    ).all()

    values = [float(m.value) for m in measurements]

    return calculate_spc(
        values,
        float(characteristic.tol_plus),
        float(characteristic.tol_minus),
        float(characteristic.sollwert)
    )


# MASCHINEN (DB!)
@app.get("/machines")
def get_machines(db: Session = Depends(get_db)):
    machines = db.query(Machine).all()

    return [
        {
            "machine_id": m.machine_id,
            "status": m.status,
            "article": m.article,
            "produced": m.produced,
            "target": m.target,
            "cycle_time": m.cycle_time
        }
        for m in machines
    ]


@app.post("/machines/status")
def update_machine_status(data: dict, db: Session = Depends(get_db)):

    machine = db.query(Machine).filter(
        Machine.machine_id == data["machine_id"]
    ).first()

    if machine:
        machine.status = data["status"]
        db.commit()

    return {"message": "updated"}