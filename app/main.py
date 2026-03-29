from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from .database import engine, Base, SessionLocal
from .models import User, Article, Process, Characteristic, Measurement, Batch, Machine
from .auth import hash_pin, verify_pin, hash_password, verify_password, generate_token, verify_token
from .models import ShopfloorUser
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

    # Admin-User anlegen falls nicht vorhanden
    if db.query(ShopfloorUser).count() == 0:
        admin = ShopfloorUser(
            username="benny",
            display_name="Benny (Admin)",
            password_hash="pbkdf2:obLD1OX2obLD1OX2obLD1CUREKRpfs1s6AYzD/KU+hPsrdqIKJinGVPbvbYHhWAt",
            role="admin",
        )
        db.add(admin)
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
    charge_nr: str = None,
    maschine: str = None,
    operator: str = None,
    db: Session = Depends(get_db)
):
    measurement = Measurement(
        characteristic_id=characteristic_id,
        value=value,
        timestamp=str(datetime.utcnow()),
        charge_nr=charge_nr,
        maschine=maschine,
        operator=operator,
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return {"message": "Messwert gespeichert"}


@app.get("/measurements/{characteristic_id}")
def get_measurements(characteristic_id: str, db: Session = Depends(get_db)):
    measurements = db.query(Measurement).filter(
        Measurement.characteristic_id == characteristic_id
    ).order_by(Measurement.timestamp).all()
    return [
        {
            "id": str(m.id),
            "characteristic_id": str(m.characteristic_id),
            "value": m.value,
            "timestamp": m.timestamp,
            "charge_nr": m.charge_nr,
            "maschine": m.maschine,
            "operator": m.operator,
        }
        for m in measurements
    ]


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
        if "article" in data:
            machine.article = data["article"]
        if "fa" in data:
            machine.fa = data["fa"]
        if "fa_target" in data:
            machine.fa_target = data["fa_target"]
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
        machine.fa = None
        machine.fa_target = None
        machine.charge = None
        machine.produced = 0

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
def reset_db():
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS machines CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS production_runs CASCADE;"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    # Maschinen neu anlegen
    db = SessionLocal()
    machines = [
        Machine(machine_id="MAPLAN GUMMI-01",  status="stopped"),
        Machine(machine_id="MAPLAN-GUMMI-02",  status="stopped"),
        Machine(machine_id="MAPLAN-SILIKON-03", status="stopped"),
        Machine(machine_id="MAPLAN-SILIKON-04", status="stopped"),
    ]
    db.add_all(machines)
    db.commit()
    db.close()

    return {"message": "DB reset done - Maschinen neu angelegt"}

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

# ─── CHARGENPROTOKOLL ────────────────────────────────────────────────────────

@app.get("/chargenprotokoll/{charge_nr}")
def get_chargenprotokoll(charge_nr: str, db: Session = Depends(get_db)):
    """Alle Daten zu einer Charge: Messungen, Fehler, Prüfprotokoll"""
    from sqlalchemy import text

    # Fehlende Spalten sicher hinzufügen falls noch nicht vorhanden
    try:
        db.execute(text("ALTER TABLE measurements ADD COLUMN IF NOT EXISTS charge_nr VARCHAR"))
        db.execute(text("ALTER TABLE measurements ADD COLUMN IF NOT EXISTS maschine VARCHAR"))
        db.execute(text("ALTER TABLE measurements ADD COLUMN IF NOT EXISTS operator VARCHAR"))
        db.execute(text("ALTER TABLE inspection_logs ADD COLUMN IF NOT EXISTS charge_nr VARCHAR"))
        db.execute(text("ALTER TABLE inspection_plans ADD COLUMN IF NOT EXISTS characteristic_id VARCHAR"))
        db.commit()
    except Exception:
        db.rollback()

    # SPC-Messungen
    try:
        measurements = db.query(Measurement).filter(
            Measurement.charge_nr == charge_nr
        ).order_by(Measurement.timestamp).all()
    except Exception:
        measurements = []

    # Fehlersammelkarten
    defects = db.query(DefectEntry).filter(
        DefectEntry.chargen_nr == charge_nr
    ).order_by(DefectEntry.created_at).all()

    # Prüfprotokoll
    try:
        inspection_logs = db.query(InspectionLog).filter(
            InspectionLog.charge_nr == charge_nr
        ).order_by(InspectionLog.created_at).all()
    except Exception:
        inspection_logs = []

    nio_gesamt = sum([
        (e.luft_fliess or 0) + (e.wkzg_verschmutzung or 0) + (e.blasen or 0) + (e.material_fehlt or 0) +
        (e.zusatzteil_feder or 0) + (e.dichtkantenfehler or 0) + (e.stechfehler or 0) + (e.doppelschnitt or 0) +
        (e.fremdkoerper_stippen or 0) + (e.werkzeugfehler or 0) + (e.abfall or 0) + (e.platzer or 0) +
        (e.blech_nio or 0) + (e.rohling or 0) + (e.sonstige or 0)
        for e in defects
    ])
    geprueft_gesamt = sum((e.geprueft or 0) for e in defects)

    return {
        "charge_nr": charge_nr,
        "zusammenfassung": {
            "messungen": len(measurements),
            "fehlersammelkarten": len(defects),
            "pruefprotokolle": len(inspection_logs),
            "nio_gesamt": nio_gesamt,
            "geprueft_gesamt": geprueft_gesamt,
            "nio_pct": round(nio_gesamt / geprueft_gesamt * 100, 2) if geprueft_gesamt else 0,
        },
        "messungen": [
            {
                "id": str(m.id),
                "characteristic_id": str(m.characteristic_id),
                "value": m.value,
                "timestamp": m.timestamp,
                "maschine": m.maschine,
                "operator": m.operator,
            }
            for m in measurements
        ],
        "fehler": [
            {
                "id": e.id,
                "datum": e.datum,
                "schicht": e.schicht,
                "maschine": e.maschine,
                "operator": e.operator,
                "geprueft": e.geprueft,
                "nio_gesamt": (
                    e.luft_fliess + e.wkzg_verschmutzung + e.blasen + e.material_fehlt +
                    e.zusatzteil_feder + e.dichtkantenfehler + e.stechfehler + e.doppelschnitt +
                    e.fremdkoerper_stippen + e.werkzeugfehler + e.abfall + e.platzer +
                    e.blech_nio + e.rohling + e.sonstige
                ),
                "fehlerarten": {k: v for k, v in {
                    "Luft-/Fließfehler": e.luft_fliess,
                    "Blasen": e.blasen,
                    "Dichtkantenfehler": e.dichtkantenfehler,
                    "Stechfehler": e.stechfehler,
                    "Fremdkörper/Stippen": e.fremdkoerper_stippen,
                    "Sonstige": e.sonstige,
                }.items() if v > 0},
            }
            for e in defects
        ],
        "pruefprotokoll": [
            {
                "id": l.id,
                "status": l.status,
                "bemerkung": l.bemerkung,
                "operator": l.operator,
                "messwert": l.messwert,
                "durchgefuehrt_um": str(l.durchgefuehrt_um) if l.durchgefuehrt_um else None,
            }
            for l in inspection_logs
        ],
    }


@app.get("/chargen")
def list_chargen(db: Session = Depends(get_db)):
    """Alle bekannten Chargennummern aus Messungen + Fehlersammelkarten"""
    from sqlalchemy import union_all, select, literal

    chargen = set()

    # Aus Messungen
    for m in db.query(Measurement.charge_nr).filter(Measurement.charge_nr != None).distinct():
        chargen.add(m.charge_nr)

    # Aus Fehlersammelkarten
    for e in db.query(DefectEntry.chargen_nr).filter(DefectEntry.chargen_nr != None).distinct():
        chargen.add(e.chargen_nr)

    # Aus Maschinen (aktive Charge)
    for mac in db.query(Machine).filter(Machine.charge != None):
        chargen.add(mac.charge)

    return sorted(list(chargen))


# ─── PRÜFPLAN ────────────────────────────────────────────────────────────────

from .models import InspectionPlan, InspectionLog

@app.post("/inspection-plans")
def create_inspection_plan(data: dict, db: Session = Depends(get_db)):
    plan = InspectionPlan(
        artikelnummer=data["artikelnummer"],
        bezeichnung=data.get("bezeichnung"),
        pruefmerkmal=data.get("pruefmerkmal"),
        characteristic_id=data.get("characteristic_id"),
        messmittel=data.get("messmittel"),
        frequenz_typ=data["frequenz_typ"],
        frequenz_wert=int(data["frequenz_wert"]),
        toleranz_plus=data.get("toleranz_plus"),
        toleranz_minus=data.get("toleranz_minus"),
        sollwert=data.get("sollwert"),
        aktiv=data.get("aktiv", True),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"message": "Prüfplan angelegt", "id": plan.id}


@app.get("/inspection-plans")
def get_inspection_plans(artikelnummer: str = None, db: Session = Depends(get_db)):
    q = db.query(InspectionPlan).filter(InspectionPlan.aktiv == True)
    if artikelnummer:
        q = q.filter(InspectionPlan.artikelnummer == artikelnummer)
    plans = q.order_by(InspectionPlan.artikelnummer, InspectionPlan.id).all()
    return [
        {
            "id": p.id,
            "artikelnummer": p.artikelnummer,
            "bezeichnung": p.bezeichnung,
            "pruefmerkmal": p.pruefmerkmal,
            "messmittel": p.messmittel,
            "frequenz_typ": p.frequenz_typ,
            "frequenz_wert": p.frequenz_wert,
            "toleranz_plus": p.toleranz_plus,
            "toleranz_minus": p.toleranz_minus,
            "sollwert": p.sollwert,
            "characteristic_id": p.characteristic_id,
            "aktiv": p.aktiv,
        }
        for p in plans
    ]


@app.put("/inspection-plans/{plan_id}")
def update_inspection_plan(plan_id: int, data: dict, db: Session = Depends(get_db)):
    plan = db.query(InspectionPlan).filter(InspectionPlan.id == plan_id).first()
    if not plan:
        return {"error": "nicht gefunden"}
    for key, val in data.items():
        if hasattr(plan, key):
            setattr(plan, key, val)
    db.commit()
    return {"message": "aktualisiert"}


@app.delete("/inspection-plans/{plan_id}")
def delete_inspection_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(InspectionPlan).filter(InspectionPlan.id == plan_id).first()
    if plan:
        plan.aktiv = False
        db.commit()
    return {"message": "deaktiviert"}


@app.post("/inspection-logs")
def create_inspection_log(data: dict, db: Session = Depends(get_db)):
    from datetime import datetime as dt
    log = InspectionLog(
        plan_id=data.get("plan_id"),
        artikelnummer=data.get("artikelnummer"),
        maschine=data.get("maschine"),
        operator=data.get("operator"),
        status=data.get("status", "durchgefuehrt"),
        messwert=data.get("messwert"),
        bemerkung=data.get("bemerkung"),
        charge_nr=data.get("charge_nr"),
        faellig_um=dt.fromisoformat(data["faellig_um"]) if data.get("faellig_um") else None,
        durchgefuehrt_um=dt.utcnow(),
    )
    db.add(log)

    # Messwert automatisch in SPC speichern wenn characteristic_id vorhanden
    messwert = data.get("messwert")
    characteristic_id = data.get("characteristic_id")
    if messwert and characteristic_id and data.get("status") == "durchgefuehrt":
        measurement = Measurement(
            characteristic_id=characteristic_id,
            value=str(messwert),
            timestamp=str(dt.utcnow()),
            charge_nr=data.get("charge_nr"),
            maschine=data.get("maschine"),
            operator=data.get("operator"),
        )
        db.add(measurement)

    db.commit()
    db.refresh(log)
    return {"message": "Protokolleintrag gespeichert", "id": log.id}


@app.get("/inspection-logs")
def get_inspection_logs(artikelnummer: str = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(InspectionLog)
    if artikelnummer:
        q = q.filter(InspectionLog.artikelnummer == artikelnummer)
    logs = q.order_by(InspectionLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "plan_id": l.plan_id,
            "artikelnummer": l.artikelnummer,
            "maschine": l.maschine,
            "operator": l.operator,
            "status": l.status,
            "messwert": l.messwert,
            "bemerkung": l.bemerkung,
            "faellig_um": str(l.faellig_um) if l.faellig_um else None,
            "durchgefuehrt_um": str(l.durchgefuehrt_um) if l.durchgefuehrt_um else None,
            "created_at": str(l.created_at),
        }
        for l in logs
    ]

# ─── ADMIN: DATENBANK BEREINIGEN ─────────────────────────────────────────────

@app.delete("/admin/clear-all")
def clear_all_data(db: Session = Depends(get_db)):
    """Löscht alle Produktionsdaten — Artikel, Messungen, Chargen, Defekte, Prüfpläne"""
    from sqlalchemy import text

    # Reihenfolge wichtig wegen Foreign Keys
    tables = [
        "inspection_logs",
        "inspection_plans",
        "defect_entries",
        "measurements",
        "characteristics",
        "processes",
        "batches",
        "articles",
    ]

    deleted = {}
    for table in tables:
        try:
            result = db.execute(text(f"DELETE FROM {table}"))
            deleted[table] = result.rowcount
        except Exception as e:
            deleted[table] = f"Fehler: {str(e)}"

    db.commit()
    return {"message": "Bereinigung abgeschlossen", "deleted": deleted}

# ─── ARTIKELMAPPE ────────────────────────────────────────────────────────────

from .models import ArticleDocument
import os, shutil

DOCS_DIR = "/mnt/data/docs"

DOC_TYPEN = {
    "zeichnung":           "Zeichnung",
    "pap":                 "Prozessablaufplan (PAP)",
    "einstellbericht":     "Einstellbericht",
    "pruefplan":           "Prüfplan-Dokument",
    "qpa":                 "QPA",
    "reklamation":         "Reklamationsbericht",
    "fehlermerkmalkatalog":"Fehlermerkmalkatalog",
}


@app.get("/artikelmappe/{artikelnummer}")
def get_artikelmappe(artikelnummer: str, db: Session = Depends(get_db)):
    """Vollständige Artikelmappe: Stammdaten + Dokumente + SPC-Übersicht"""

    # Stammdaten
    article = db.query(Article).filter(
        Article.artikelnummer == artikelnummer
    ).first()

    # Dokumente
    docs = db.query(ArticleDocument).filter(
        ArticleDocument.artikelnummer == artikelnummer
    ).order_by(ArticleDocument.doc_typ, ArticleDocument.created_at.desc()).all()

    # Prüfmerkmale mit letztem Cpk
    processes = db.query(Process).filter(
        Process.article_id == article.id if article else None
    ).all() if article else []

    merkmale_overview = []
    for proc in processes:
        chars = db.query(Characteristic).filter(
            Characteristic.process_id == proc.id
        ).all()
        for c in chars:
            measurements = db.query(Measurement).filter(
                Measurement.characteristic_id == c.id
            ).all()
            values = [float(m.value) for m in measurements if m.value]
            cpk = None
            status = "keine Daten"
            if len(values) >= 5:
                from .spc import calculate_spc
                try:
                    spc = calculate_spc(values, float(c.tol_plus), float(c.tol_minus), float(c.sollwert))
                    cpk = spc["cpk"]
                    status = spc["status"]
                except:
                    pass
            merkmale_overview.append({
                "prozess": proc.name,
                "merkmal": c.name,
                "sollwert": c.sollwert,
                "tol_plus": c.tol_plus,
                "tol_minus": c.tol_minus,
                "messmittel": c.messmittel,
                "frequenz": c.frequenz,
                "n_messungen": len(values),
                "cpk": cpk,
                "status": status,
            })

    return {
        "artikelnummer": artikelnummer,
        "stammdaten": {
            "bezeichnung": article.bezeichnung if article else None,
            "material": article.material if article else None,
            "werkzeug": article.werkzeug if article else None,
            "kavitaeten": article.kavitaeten if article else None,
            "revision": article.revision if article else None,
        } if article else None,
        "dokumente": [
            {
                "id": d.id,
                "doc_typ": d.doc_typ,
                "doc_typ_label": DOC_TYPEN.get(d.doc_typ, d.doc_typ),
                "bezeichnung": d.bezeichnung,
                "revision": d.revision,
                "dateiname": d.dateiname,
                "notiz": d.notiz,
                "erstellt_von": d.erstellt_von,
                "created_at": str(d.created_at),
                "download_url": f"/docs/download/{d.id}" if d.dateipfad else None,
            }
            for d in docs
        ],
        "pruefmerkmale": merkmale_overview,
    }


@app.post("/artikelmappe/{artikelnummer}/upload")
async def upload_document(
    artikelnummer: str,
    doc_typ: str,
    bezeichnung: str = "",
    revision: str = "",
    notiz: str = "",
    erstellt_von: str = "",
    file: bytes = None,
    db: Session = Depends(get_db),
    request = None
):
    from fastapi import Request, UploadFile, File, Form
    return {"message": "Verwende den Multipart-Endpoint /artikelmappe/upload"}


from fastapi import UploadFile, File, Form

@app.post("/artikelmappe/upload")
async def upload_document_multipart(
    artikelnummer: str = Form(...),
    doc_typ: str = Form(...),
    bezeichnung: str = Form(""),
    revision: str = Form(""),
    notiz: str = Form(""),
    erstellt_von: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    import base64

    file_bytes = await file.read()
    # Max 10MB
    if len(file_bytes) > 10 * 1024 * 1024:
        return {"error": "Datei zu groß (max. 10 MB)"}

    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
    safe_name = file.filename.replace(" ", "_")

    doc = ArticleDocument(
        artikelnummer=artikelnummer,
        doc_typ=doc_typ,
        bezeichnung=bezeichnung or file.filename,
        revision=revision,
        dateiname=safe_name,
        dateipfad=f"base64:{file_b64}",  # Base64 in DB
        notiz=notiz,
        erstellt_von=erstellt_von,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"message": "Dokument hochgeladen", "id": doc.id}


@app.get("/docs/download/{doc_id}")
async def download_document(doc_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    import base64

    doc = db.query(ArticleDocument).filter(ArticleDocument.id == doc_id).first()
    if not doc:
        return {"error": "Dokument nicht gefunden"}

    if doc.dateipfad and doc.dateipfad.startswith("base64:"):
        file_bytes = base64.b64decode(doc.dateipfad[7:])
        return Response(
            content=file_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{doc.dateiname}"'}
        )
    return {"error": "Datei nicht verfügbar"}


@app.delete("/artikelmappe/dokument/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(ArticleDocument).filter(ArticleDocument.id == doc_id).first()
    if doc:
        # Datei löschen
        if doc.dateipfad and os.path.exists(doc.dateipfad):
            os.remove(doc.dateipfad)
        db.delete(doc)
        db.commit()
    return {"message": "Dokument gelöscht"}


@app.get("/artikelmappe")
def list_artikelmappen(db: Session = Depends(get_db)):
    """Alle Artikel mit Dokumentanzahl"""
    articles = db.query(Article).all()
    result = []
    for a in articles:
        doc_count = db.query(ArticleDocument).filter(
            ArticleDocument.artikelnummer == a.artikelnummer
        ).count()
        result.append({
            "artikelnummer": a.artikelnummer,
            "bezeichnung": a.bezeichnung,
            "material": a.material,
            "revision": a.revision,
            "doc_count": doc_count,
        })
    return result

# ─── AUTH / BENUTZER ─────────────────────────────────────────────────────────

@app.post("/auth/login")
def login_user(data: dict, db: Session = Depends(get_db)):
    username = data.get("username", "").lower().strip()
    password = data.get("password", "")

    user = db.query(ShopfloorUser).filter(
        ShopfloorUser.username == username,
        ShopfloorUser.aktiv == True
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return {"error": "Benutzername oder Passwort falsch"}

    # Last login updaten
    user.last_login = datetime.utcnow()
    db.commit()

    token = generate_token(user.id, user.username, user.role)

    return {
        "token": token,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "role": user.role,
    }


@app.post("/auth/verify")
def verify_user_token(data: dict):
    token = data.get("token", "")
    user_info = verify_token(token)
    if not user_info:
        return {"error": "Token ungültig oder abgelaufen"}
    return user_info


@app.get("/auth/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(ShopfloorUser).filter(ShopfloorUser.aktiv == True).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "role": u.role,
            "last_login": str(u.last_login) if u.last_login else None,
        }
        for u in users
    ]


@app.post("/auth/users")
def create_user(data: dict, db: Session = Depends(get_db)):
    username = data.get("username", "").lower().strip()
    password = data.get("password", "")
    role = data.get("role", "produktion")

    if not username or not password:
        return {"error": "Benutzername und Passwort erforderlich"}

    existing = db.query(ShopfloorUser).filter(ShopfloorUser.username == username).first()
    if existing:
        return {"error": "Benutzername bereits vergeben"}

    user = ShopfloorUser(
        username=username,
        display_name=data.get("display_name", username),
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Benutzer angelegt", "id": user.id}


@app.delete("/auth/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(ShopfloorUser).filter(ShopfloorUser.id == user_id).first()
    if user:
        user.aktiv = False
        db.commit()
    return {"message": "Benutzer deaktiviert"}
