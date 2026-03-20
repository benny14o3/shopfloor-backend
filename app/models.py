import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    pin_hash = Column(String, nullable=False)
    active = Column(Boolean, default=True)

from sqlalchemy import Column, String, Integer
import uuid
from sqlalchemy.dialects.postgresql import UUID
from .database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    artikelnummer = Column(String, nullable=False)
    bezeichnung = Column(String)

    material = Column(String)
    werkzeug = Column(String)

    kavitaeten = Column(Integer)

    revision = Column(String)

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

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

class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"))

    characteristic_id = Column(UUID(as_uuid=True), ForeignKey("characteristics.id"))

    value = Column(String)

    timestamp = Column(String)
    

class Batch(Base):
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"))

    chargennummer = Column(String)

    maschine = Column(String)

    operator = Column(String)

    materialcharge = Column(String)

    start_time = Column(String)

from sqlalchemy import Column, Integer, String

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, unique=True, index=True)
    status = Column(String)
    article = Column(String, nullable=True)
    produced = Column(Integer, default=0)
    target = Column(Integer, nullable=True)
    cycle_time = Column(Integer, nullable=True)

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class ProductionRun(Base):
    __tablename__ = "production_runs"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String)
    article = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    quantity = Column(Integer, default=0)