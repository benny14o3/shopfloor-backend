import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    pin_hash = Column(String, nullable=False)
    active = Column(Boolean, default=True)


class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artikelnummer = Column(String, nullable=False)
    bezeichnung = Column(String)
    material = Column(String)
    werkzeug = Column(String)
    kavitaeten = Column(Integer)
    revision = Column(String)


class Process(Base):
    __tablename__ = "processes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"))
    nummer = Column(Integer)
    name = Column(String)
    maschine = Column(String)


class Characteristic(Base):
    __tablename__ = "characteristics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey("processes.id"))
    name = Column(String)
    sollwert = Column(String)
    tol_plus = Column(String)
    tol_minus = Column(String)
    messmittel = Column(String)
    frequenz = Column(String)


class Batch(Base):
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"))
    chargennummer = Column(String)
    maschine = Column(String)
    operator = Column(String)
    materialcharge = Column(String)
    start_time = Column(String)


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)
    characteristic_id = Column(UUID(as_uuid=True), ForeignKey("characteristics.id"))
    value = Column(String)
    timestamp = Column(String)


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, unique=True, index=True)
    status = Column(String)
    article = Column(String, nullable=True)
    produced = Column(Integer, default=0)
    target = Column(Integer, nullable=True)
    cycle_time = Column(Integer, nullable=True)
    fa = Column(String, nullable=True)          # Fertigungsauftrag-Nummer
    fa_target = Column(Integer, nullable=True)   # Soll-Menge FA
    charge = Column(String, nullable=True)        # Aktuelle Chargen-Nr.


class ProductionRun(Base):
    __tablename__ = "production_runs"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String)
    article = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    quantity = Column(Integer, default=0)


class DefectEntry(Base):
    __tablename__ = "defect_entries"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, nullable=True)
    artikelnummer = Column(String, nullable=True)
    auftrag_nr = Column(String, nullable=True)
    chargen_nr = Column(String, nullable=True)
    maschine = Column(String, nullable=True)
    operator = Column(String, nullable=True)
    schicht = Column(String, nullable=True)       # Früh / Spät / Nacht
    datum = Column(String, nullable=True)
    geprueft = Column(Integer, default=0)         # Geprüfte Teile
    nacharbeit = Column(Integer, default=0)
    anfahrausschuss = Column(Integer, default=0)
    # Fehlerarten als einzelne Zähler
    luft_fliess = Column(Integer, default=0)
    wkzg_verschmutzung = Column(Integer, default=0)
    blasen = Column(Integer, default=0)
    material_fehlt = Column(Integer, default=0)
    zusatzteil_feder = Column(Integer, default=0)
    dichtkantenfehler = Column(Integer, default=0)
    stechfehler = Column(Integer, default=0)
    doppelschnitt = Column(Integer, default=0)
    fremdkoerper_stippen = Column(Integer, default=0)
    werkzeugfehler = Column(Integer, default=0)
    abfall = Column(Integer, default=0)
    platzer = Column(Integer, default=0)
    blech_nio = Column(Integer, default=0)
    rohling = Column(Integer, default=0)
    sonstige = Column(Integer, default=0)
    notiz = Column(String, nullable=True)
    # Fehlerorte je Fehlerart (JSON-String)
    fehlerorte = Column(String, nullable=True)
    # Zusatzfelder
    typ = Column(String, nullable=True)
    material = Column(String, nullable=True)
    bindung = Column(String, nullable=True)
    freigabe = Column(String, nullable=True)
    federkontrolle = Column(String, nullable=True)   # "io" / "nio" / None
    bindungspruefung = Column(String, nullable=True) # "io" / "nio" / None
    created_at = Column(DateTime, default=datetime.utcnow)


class InspectionPlan(Base):
    """Prüfplan: definiert Prüfaufgaben pro Artikel mit Frequenz"""
    __tablename__ = "inspection_plans"

    id = Column(Integer, primary_key=True, index=True)
    artikelnummer = Column(String, nullable=False, index=True)
    bezeichnung = Column(String, nullable=True)       # Prüfaufgabe
    pruefmerkmal = Column(String, nullable=True)      # Was wird geprüft
    messmittel = Column(String, nullable=True)
    frequenz_typ = Column(String, nullable=False)     # "zeit" / "schicht" / "stueckzahl"
    frequenz_wert = Column(Integer, nullable=False)   # z.B. 60 (min) / 1 (schicht) / 500 (stück)
    toleranz_plus = Column(String, nullable=True)
    toleranz_minus = Column(String, nullable=True)
    sollwert = Column(String, nullable=True)
    aktiv = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InspectionLog(Base):
    """Prüfprotokoll: jede durchgeführte oder überfällige Prüfung"""
    __tablename__ = "inspection_logs"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("inspection_plans.id"))
    artikelnummer = Column(String, nullable=True)
    maschine = Column(String, nullable=True)
    operator = Column(String, nullable=True)
    status = Column(String, nullable=False)           # "faellig" / "durchgefuehrt" / "quittiert"
    messwert = Column(String, nullable=True)
    bemerkung = Column(String, nullable=True)
    faellig_um = Column(DateTime, nullable=True)
    durchgefuehrt_um = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
