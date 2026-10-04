"""HTTP routes for Phases 2-8. Each handler is a thin call into a tested module."""
from fastapi import APIRouter, Body, Depends, File, UploadFile

import agent
import evaluate
import prediction
import profile as profile_mod
import rules
import services
import vision
import bayes
from deps import get_db
from errors import ApiError

router = APIRouter(prefix="/api")


@router.get("/profile")
def get_profile(conn=Depends(get_db)):
    return profile_mod.build_profile(conn)


@router.get("/profile/{category}")
def get_category_profile(category: str, conn=Depends(get_db)):
    return profile_mod.category_profile(profile_mod.build_profile(conn), category)


@router.get("/rules")
def rule_definitions():
    return rules.RULES


@router.post("/analyze/rules")
def analyze_rules(body: dict = Body(...), conn=Depends(get_db)):
    return services.analyze_rules(conn, body)


@router.get("/bayes/structure")
def bayes_structure():
    return bayes.network_structure()


@router.post("/analyze/bayes")
def analyze_bayes(body: dict = Body(...), conn=Depends(get_db)):
    return services.analyze_bayes(conn, body)


@router.post("/agent/process")
def agent_process(body: dict = Body(...), conn=Depends(get_db)):
    return agent.process(conn, body)


@router.post("/agent/answer")
def agent_answer(body: dict = Body(...), conn=Depends(get_db)):
    try:
        txn_id = int(body.get("txn_id"))
    except (TypeError, ValueError):
        raise ApiError(["txn_id is required"])
    return agent.answer(conn, txn_id, body.get("answer"))


@router.get("/agent/runs/{txn_id}")
def agent_run(txn_id: int, conn=Depends(get_db)):
    return agent.run_view(conn, txn_id)


@router.get("/prediction")
def get_prediction(conn=Depends(get_db)):
    return prediction.predict_all(conn)


@router.get("/evaluation")
def get_evaluation(conn=Depends(get_db)):
    return evaluate.run_evaluation(conn)


@router.get("/dashboard/overview")
def dashboard_overview(conn=Depends(get_db)):
    return services.dashboard_overview(conn)


@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Screenshot is read into memory, sent to Gemini and discarded. Nothing is written to disk or the database."""
    if file.content_type not in ("image/png", "image/jpeg"):
        raise ApiError(["Please upload a PNG or JPG image."], 415)
    data = await file.read()
    if len(data) > 6_000_000:
        raise ApiError(["The image is larger than 6 MB."], 413)
    return vision.extract(data, file.content_type)
