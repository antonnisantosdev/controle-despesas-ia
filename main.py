from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def inicio():
    return {"message": "A API de finanças está funcionando!"}