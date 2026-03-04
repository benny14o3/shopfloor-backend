from fastapi import FastAPI
from .database import engine, Base

app = FastAPI(title="Formteile Fritsch Shopfloor API")

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Shopfloor API läuft"}
