from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from .database import engine, Base, SessionLocal
from .models import User, Article, Process, Characteristic, Measurement, Batch, Machine
from .auth import hash_pin, verify_pin
from .spc import calculate_spc
from .models import ProductionRun

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
            "cycle_time": m.cycle_time,
            "fa": m.fa,
            "fa_target": m.fa_target,
            "charge": m.charge
        }
        for m in machines
    ]


@app.post("/machines/status")
def update_machine_status(data: dict, db: Session = Depends(get_db)):

    machine = db.query(Machine).filter(
        Machine.machine_id == data["machine_id"]
    ).first()

    if machine:
        if "status" in data:
            machine.status = data["status"]
        if "charge" in data:
            machine.charge = data["charge"]
        db.commit()

    return {"message": "updated"}


@app.post("/production/start")
def start_production(data: dict, db: Session = Depends(get_db)):

    run = ProductionRun(
        machine_id=data["machine_id"],
        article=data["article"]
    )

    db.add(run)

    machine = db.query(Machine).filter(
        Machine.machine_id == data["machine_id"]
    ).first()

    if machine:
        machine.article = data["article"]
        machine.fa = data.get("fa")
        machine.fa_target = data.get("fa_target")

    db.commit()

    return {"message": "started"}

@app.post("/production/stop")
def stop_production(data: dict, db: Session = Depends(get_db)):

    run = db.query(ProductionRun).filter(
        ProductionRun.machine_id == data["machine_id"],
        ProductionRun.end_time == None
    ).first()

    if run:
        run.end_time = datetime.utcnow()
        run.quantity = data.get("quantity", 0)

    # Maschine zurücksetzen
    machine = db.query(Machine).filter(
        Machine.machine_id == data["machine_id"]
    ).first()

    if machine:
        machine.article = None

    db.commit()

    return {"message": "stopped"}


@app.get("/production/active")
def get_active_production(db: Session = Depends(get_db)):

    runs = db.query(ProductionRun).filter(
        ProductionRun.end_time == None
    ).all()

    return [
        {
            "machine_id": r.machine_id,
            "article": r.article,
            "start": r.start_time,
            "quantity": r.quantity
        }
        for r in runs
    ]

@app.get("/reset-db")
def reset_db(db: Session = Depends(get_db)):

    db.execute("DROP TABLE IF EXISTS machines CASCADE;")
    db.execute("DROP TABLE IF EXISTS production_runs CASCADE;")
    db.commit()

    Base.metadata.create_all(bind=engine)

    return {"message": "DB reset done"}

# ─── FEHLERSAMMELKARTE ──────────────────────────────────────────────────────

from .models import DefectEntry

@app.post("/defects")
def create_defect(data: dict, db: Session = Depends(get_db)):
    entry = DefectEntry(
        article_id=data.get("article_id"),
        artikelnummer=data.get("artikelnummer"),
        auftrag_nr=data.get("auftrag_nr"),
        chargen_nr=data.get("chargen_nr"),
        maschine=data.get("maschine"),
        operator=data.get("operator"),
        schicht=data.get("schicht"),
        datum=data.get("datum"),
        geprueft=int(data.get("geprueft", 0)),
        nacharbeit=int(data.get("nacharbeit", 0)),
        anfahrausschuss=int(data.get("anfahrausschuss", 0)),
        luft_fliess=int(data.get("luft_fliess", 0)),
        wkzg_verschmutzung=int(data.get("wkzg_verschmutzung", 0)),
        blasen=int(data.get("blasen", 0)),
        material_fehlt=int(data.get("material_fehlt", 0)),
        zusatzteil_feder=int(data.get("zusatzteil_feder", 0)),
        dichtkantenfehler=int(data.get("dichtkantenfehler", 0)),
        stechfehler=int(data.get("stechfehler", 0)),
        doppelschnitt=int(data.get("doppelschnitt", 0)),
        fremdkoerper_stippen=int(data.get("fremdkoerper_stippen", 0)),
        werkzeugfehler=int(data.get("werkzeugfehler", 0)),
        abfall=int(data.get("abfall", 0)),
        platzer=int(data.get("platzer", 0)),
        blech_nio=int(data.get("blech_nio", 0)),
        rohling=int(data.get("rohling", 0)),
        sonstige=int(data.get("sonstige", 0)),
        notiz=data.get("notiz"),
        fehlerorte=data.get("fehlerorte"),        # JSON string
        typ=data.get("typ"),
        material=data.get("material"),
        bindung=data.get("bindung"),
        freigabe=data.get("freigabe"),
        federkontrolle=data.get("federkontrolle"),
        bindungspruefung=data.get("bindungspruefung"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"message": "Gespeichert", "id": entry.id}


@app.get("/defects")
def get_defects(artikelnummer: str = None, db: Session = Depends(get_db)):
    q = db.query(DefectEntry)
    if artikelnummer:
        q = q.filter(DefectEntry.artikelnummer == artikelnummer)
    entries = q.order_by(DefectEntry.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "artikelnummer": e.artikelnummer,
            "auftrag_nr": e.auftrag_nr,
            "chargen_nr": e.chargen_nr,
            "maschine": e.maschine,
            "operator": e.operator,
            "schicht": e.schicht,
            "datum": e.datum,
            "geprueft": e.geprueft,
            "nacharbeit": e.nacharbeit,
            "anfahrausschuss": e.anfahrausschuss,
            "nio_gesamt": (
                e.luft_fliess + e.wkzg_verschmutzung + e.blasen + e.material_fehlt +
                e.zusatzteil_feder + e.dichtkantenfehler + e.stechfehler + e.doppelschnitt +
                e.fremdkoerper_stippen + e.werkzeugfehler + e.abfall + e.platzer +
                e.blech_nio + e.rohling + e.sonstige
            ),
            "anteil_nio": round(
                (e.luft_fliess + e.wkzg_verschmutzung + e.blasen + e.material_fehlt +
                 e.zusatzteil_feder + e.dichtkantenfehler + e.stechfehler + e.doppelschnitt +
                 e.fremdkoerper_stippen + e.werkzeugfehler + e.abfall + e.platzer +
                 e.blech_nio + e.rohling + e.sonstige) / e.geprueft * 100, 2
            ) if e.geprueft else 0,
            "fehler": {
                "Luft-/Fließfehler": e.luft_fliess,
                "Wkzg.-Verschmutzung": e.wkzg_verschmutzung,
                "Blasen": e.blasen,
                "Material fehlt": e.material_fehlt,
                "Zusatzteil/Feder": e.zusatzteil_feder,
                "Dichtkantenfehler": e.dichtkantenfehler,
                "Stechfehler": e.stechfehler,
                "Doppelschnitt": e.doppelschnitt,
                "Fremdkörper/Stippen": e.fremdkoerper_stippen,
                "Werkzeugfehler": e.werkzeugfehler,
                "Abfall": e.abfall,
                "Platzer": e.platzer,
                "Blech n.i.O.": e.blech_nio,
                "Rohling": e.rohling,
                "Sonstige": e.sonstige,
            },
            "notiz": e.notiz,
            "fehlerorte": e.fehlerorte,
            "typ": e.typ,
            "material": e.material,
            "bindung": e.bindung,
            "freigabe": e.freigabe,
            "federkontrolle": e.federkontrolle,
            "bindungspruefung": e.bindungspruefung,
            "created_at": str(e.created_at),
        }
        for e in entries
    ]
