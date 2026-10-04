"""FastAPI layer: thin wrappers around transactions.py, csv_import.py and seed.py.
Run from this folder:  uvicorn main:app --reload"""
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
from fastapi import APIRouter, Body, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import transactions as tx
from constants import ALL_CATEGORIES, PAYMENT_METHODS
from csv_import import import_csv
from db import get_conn, init_db
from deps import get_db
from errors import ApiError
from routes_ai import router as ai_router
from seed import reset_demo_data

app = FastAPI(title="Personal Financial Intelligence")
app = FastAPI(title="Personal Financial Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://finance-ai-lake-three.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


@app.on_event("startup")
def startup():
    conn = get_conn()
    init_db(conn)
    conn.close()


@app.exception_handler(ApiError)
async def api_error_handler(request, exc):
    return JSONResponse(status_code=exc.status, content={"detail": {"errors": exc.errors}})


def _fail(errors, code=422):
    raise HTTPException(status_code=code, detail={"errors": errors})


@api.get("/meta")
def meta():
    return {"categories": ALL_CATEGORIES, "payment_methods": PAYMENT_METHODS}


@api.get("/transactions")
def list_transactions(month: str = None, category: str = None, search: str = None, conn=Depends(get_db)):
    return tx.list_transactions(conn, month or None, category or None, search or None)


@api.get("/transactions/months")
def months(conn=Depends(get_db)):
    return tx.list_months(conn)


@api.post("/transactions", status_code=201)
def add_transaction(body: dict = Body(...), conn=Depends(get_db)):
    created, errors = tx.add_transaction(conn, body)
    if errors:
        _fail(errors)
    return created


@api.put("/transactions/{txn_id}")
def edit_transaction(txn_id: int, body: dict = Body(...), conn=Depends(get_db)):
    if tx.get_transaction(conn, txn_id) is None:
        _fail(["Transaction not found"], 404)
    updated, errors = tx.update_transaction(conn, txn_id, body)
    if errors:
        _fail(errors)
    return updated


@api.delete("/transactions/{txn_id}")
def delete_transaction(txn_id: int, conn=Depends(get_db)):
    if not tx.delete_transaction(conn, txn_id):
        _fail(["Transaction not found"], 404)
    return {"deleted": txn_id}


@api.post("/transactions/import")
def import_transactions(file: UploadFile = File(...), conn=Depends(get_db)):
    raw = file.file.read()
    if len(raw) > 2_000_000:
        _fail(["File is larger than 2 MB"], 413)
    try:
        return import_csv(conn, raw)
    except UnicodeDecodeError:
        _fail(["The file is not UTF-8 text. Save it as CSV (UTF-8) and try again."], 400)


@api.get("/dashboard/summary")
def dashboard_summary(month: str = None, conn=Depends(get_db)):
    return tx.month_summary(conn, month or date.today().strftime("%Y-%m"))


@api.post("/demo/reset")
def reset(conn=Depends(get_db)):
    return {"transactions": reset_demo_data(conn)}


app.include_router(api)
app.include_router(ai_router)
