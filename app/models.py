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
