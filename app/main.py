from fastapi import FastAPI

app = FastAPI(title="Formteile Fritsch Shopfloor API")

@app.get("/")
def root():
    return {"message": "Shopfloor API läuft"}
