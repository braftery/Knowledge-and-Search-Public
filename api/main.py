"""Harbor Health knowledge API.

One process serves the JSON API and, when web/dist exists, the built front end.
Until that build exists, the site root is a plain placeholder.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from api.catalog import ILLUSTRATIVE
from api.errors import APIError, world_name
from api.plan_data import drug_price_view, member_profile_view, member_record_view, visit_cost_view
from api.present import (
    activity_view,
    as_of_view,
    author_edits_view,
    author_queue_view,
    calls_view,
    changes_view,
    channels_view,
    conflicts_view,
    copies_view,
    document_view,
    documents_view,
    drift_view,
    expired_view,
    explore_view,
    extraction_view,
    feedback_author_view,
    feedback_open_view,
    feedback_product_view,
    feedback_summary_view,
    gaps_view,
    guided_view,
    inbox_view,
    insights_view,
    legal_drift_view,
    legal_queue_view,
    member_topics_view,
    my_work_view,
    portal_events_view,
    portal_one_view,
    portal_quick_view,
    portal_units_view,
    quality_view,
    questions_view,
    scope_view,
    search_prompts,
    session_view,
    today_view,
    undo_payload,
    unit_view,
    units_view,
    versions_view,
    wrapups_view,
)
from api.service import (
    desk_search,
    explore_ask,
    run_acknowledge,
    run_wrapup,
    member_helped,
    member_turn,
    open_explore,
    reset_database,
    reset_explore,
    run_approve_author,
    run_approve_author_all,
    run_approve_drift,
    run_approve_legal,
    run_approve_legal_all,
    run_confirm,
    run_decline,
    run_drift,
    run_drift_send,
    run_edit_gap,
    run_edit_returned,
    run_escalate,
    run_extract,
    run_feedback,
    run_gap,
    run_keep,
    run_publish,
    run_resolve,
    run_resolve_drift,
    run_resolve_feedback,
    run_return_drift,
    run_score,
    run_search,
    run_send_gap,
    run_send_returned,
    run_search_both,
    run_today,
    portal_answer,
    run_undo,
    set_explore_page,
    set_live_mode,
    set_step,
)
from api.store import COOKIE, Session, open_session

logger = logging.getLogger("api")
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"
PLACEHOLDER = Path(__file__).resolve().parent / "placeholder.html"

app = FastAPI(title="Harbor Health Knowledge API", docs_url="/api/docs", openapi_url="/api/openapi.json")
_ALLOWED_ORIGINS = [
    "https://harbor-knowledge.onrender.com",
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WorldBody(BaseModel):
    world: str = "guided"


class PublishBody(WorldBody):
    idempotency_key: str = ""
    text: str | None = None
    member_text: str | None = None


class VerifyBody(BaseModel):
    member_id: str = ""
    date_of_birth: str = ""
    call_id: str = ""


class ResetBody(BaseModel):
    mode: str = "start"


class StepBody(BaseModel):
    step: int


class LiveBody(WorldBody):
    enabled: bool = False


class UnitBody(WorldBody):
    unit_id: str | None = None


class AuthorBody(WorldBody):
    unit_id: str


class ReasonBody(WorldBody):
    unit_id: str
    reason: str = ""


class ConflictBody(WorldBody):
    conflict_id: str | None = None
    reason: str = ""


class SearchBody(WorldBody):
    role: str
    query: str
    record: bool = True


class BothBody(WorldBody):
    query: str
    record: bool = True


class GapBody(WorldBody):
    action: str
    reason: str = ""


class DraftBody(WorldBody):
    text: str = ""
    member_text: str = ""


class DriftBody(WorldBody):
    kind: str


class DriftReturnBody(WorldBody):
    reason: str = ""


class ReviewBody(WorldBody):
    action: str
    reason: str = ""
    text: str | None = None
    member_text: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    audience: list[str] | str | None = None


class PlaceholderSourceBody(WorldBody):
    kind: str
    ref: str = ""
    quote: str = ""
    owner_role: str = ""
    question: str = ""


class PlaceholderFillBody(WorldBody):
    text: str = ""


class AddUnitBody(WorldBody):
    span: str = ""
    title: str = ""
    type: str = "procedure"
    audience: list[str] | None = None
    tags: list[str] | None = None


class SourceAnswerBody(WorldBody):
    statement: str = ""
    signer: str = ""
    no_policy: bool = False


class DismissBody(WorldBody):
    kind: str = ""
    reason: str = ""
    unit_id: str = ""


class NoSourceBody(WorldBody):
    reason: str = ""


class AuthorDriftActionBody(WorldBody):
    action: str
    reason: str = ""
    text: str = ""


class DriftResolveBody(WorldBody):
    note: str = ""


class FeedbackBody(WorldBody):
    source: str
    role: str
    kind: str
    question: str = ""
    unit_id: str = ""
    note: str = ""
    signals: dict | None = None


class ResolveFeedbackBody(WorldBody):
    resolution: str = ""


class UndoBody(BaseModel):
    world: str = "guided"
    role: str = ""
    resource: str = ""


class ExploreOpenBody(BaseModel):
    role: str


class ExplorePageBody(BaseModel):
    page: str


class ExploreAskBody(BaseModel):
    role: str
    query: str
    member_id: str = ""
    verified: bool = False


class DeskBody(BaseModel):
    role: str
    query: str
    call_reason: str = ""


class MemberBody(BaseModel):
    question: str = ""
    topic: int | None = None
    member_id: str = ""
    channel: str = ""
    call_id: str = ""


class TagBody(BaseModel):
    world: str = "guided"
    audience: str = ""
    domain: str = ""
    tags: list[str] = []


class ReviewExtendBody(BaseModel):
    world: str = "explore"
    unit_id: str
    review_by: str
    reason: str = ""


class ReviewRetireBody(BaseModel):
    world: str = "explore"
    unit_id: str
    reason: str = ""


class CallerBody(BaseModel):
    member_id: str
    caller_name: str
    relationship: str


class WebhookBody(BaseModel):
    url: str
    events: list[str] = []
    world: str = "explore"


class HelpedBody(BaseModel):
    helped: bool
    question: str = ""
    unit_id: str = ""


class WrapupBody(BaseModel):
    world: str = "explore"
    role: str = ""
    call_id: str = ""
    call_reason: str = ""
    unit_ids: list[str] = []
    displayed_units: list[dict] = []
    read_verbatim: bool | None = None
    outcome: str = ""
    note: str = ""


class AcknowledgeBody(BaseModel):
    world: str = "explore"
    role: str = ""
    unit_id: str = ""
    version: int | None = None


def get_session(request: Request, response: Response) -> Session:
    session = open_session(request.cookies.get(COOKIE))
    if request.cookies.get(COOKIE) != session.id:
        response.set_cookie(
            COOKIE,
            session.id,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24 * 14,
            secure=request.url.scheme == "https",
        )
    return session


def _unverified_figure(conn, kind: str) -> dict:
    from api.plan_data import unverified_rule

    rule = unverified_rule(conn)
    amount = "price" if kind == "price" else "cost"
    display = "price_display" if kind == "price" else "cost_display"
    return {
        "available": False,
        amount: None,
        display: "",
        "withheld_reason": rule["text"],
        "units": rule["units"],
        "illustrative": True,
        "note": "Illustrative, made-up data",
        "verified": False,
    }


def _world(value: str | None, default: str = "guided") -> str:
    return world_name(value, default)


def _read(session: Session, world: str, builder):
    with session._lock:
        with session.connection(world) as conn:
            return builder(conn)


def _bound_role(session: Session, supplied: str) -> str:
    from src.finish import resolve_explore_role

    if not session.explore_ready():
        raise APIError("Open an Explore role before using the sandbox.")
    return resolve_explore_role(session, supplied)


@app.middleware("http")
async def remember_client_ip(request: Request, call_next):
    from src.engine import _CLIENT_IP

    forwarded = request.headers.get("x-forwarded-for", "")
    address = forwarded.split(",")[0].strip()
    if not address and request.client is not None:
        address = request.client.host or ""
    token = _CLIENT_IP.set(address)
    try:
        return await call_next(request)
    finally:
        _CLIENT_IP.reset(token)


@app.exception_handler(APIError)
async def on_api_error(_request: Request, exc: APIError):
    from src.finish import problem_body

    return JSONResponse(problem_body(exc.message, exc.status, exc.allowed), status_code=exc.status)


@app.exception_handler(RequestValidationError)
async def on_validation(_request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if not errors:
        message = "The request has the wrong shape."
    else:
        loc = [str(part) for part in errors[0].get("loc", []) if part not in ("body", "query", "path")]
        field = ".".join(loc) or "request"
        message = f"The field {field} is missing or invalid."
    from src.finish import problem_body

    return JSONResponse(problem_body(message, 400), status_code=400)


@app.exception_handler(Exception)
async def on_unexpected(_request: Request, exc: Exception):
    logger.error("request failed: %s", type(exc).__name__)
    from src.finish import problem_body

    return JSONResponse(problem_body("The service could not complete that action.", 500), status_code=500)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "harbor-knowledge", "illustrative": True, "note": ILLUSTRATIVE}


@app.get("/api/session")
def session_get(session: Session = Depends(get_session)):
    with session._lock:
        with session.connection("guided") as conn:
            return session_view(session, conn)


@app.post("/api/session/reset")
def session_reset(body: ResetBody, session: Session = Depends(get_session)):
    return reset_database(session, body.mode)


@app.post("/api/session/jump-short")
def session_jump(session: Session = Depends(get_session)):
    return reset_database(session, "short")


@app.get("/api/demo")
def demo_get(session: Session = Depends(get_session)):
    return _read(session, "guided", lambda conn: guided_view(session, conn))


@app.post("/api/demo/step")
def demo_step(body: StepBody, session: Session = Depends(get_session)):
    return set_step(session, body.step)


@app.post("/api/settings/live")
def settings_live(body: LiveBody, session: Session = Depends(get_session)):
    return set_live_mode(session, _world(body.world), body.enabled)


@app.get("/api/demo/today")
def today_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), today_view)


@app.post("/api/demo/today")
def today_post(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_today(session, _world(body.world))


@app.get("/api/demo/extraction")
def extraction_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), extraction_view)


@app.post("/api/demo/extract")
def extract_post(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_extract(session, _world(body.world))


@app.post("/api/demo/confirm-tags")
def confirm_post(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_confirm(session, _world(body.world))


@app.get("/api/demo/copies")
def copies_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), copies_view)


@app.post("/api/demo/keep-canonical")
def keep_post(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_keep(session, _world(body.world))


@app.post("/api/demo/escalate")
def escalate_post(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_escalate(session, _world(body.world))


@app.get("/api/legal/queue")
def legal_queue(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), legal_queue_view)


@app.get("/api/author/queue")
def author_queue_route(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), author_queue_view)


@app.get("/api/conflicts")
def conflicts_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), conflicts_view)


@app.get("/api/legal/inbox")
def inbox_get(world: str = "explore", session: Session = Depends(get_session)):
    return _read(session, _world(world, "explore"), inbox_view)


@app.post("/api/legal/approve")
def legal_approve(body: UnitBody | None = None, session: Session = Depends(get_session)):
    body = body or UnitBody()
    return run_approve_legal(session, _world(body.world), body.unit_id)


@app.post("/api/legal/approve-all")
def legal_approve_all(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_approve_legal_all(session, _world(body.world))


@app.post("/api/author/approve")
def author_approve(body: AuthorBody, session: Session = Depends(get_session)):
    return run_approve_author(session, _world(body.world), body.unit_id)


@app.post("/api/author/approve-all")
def author_approve_all(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_approve_author_all(session, _world(body.world))


@app.get("/api/author/edits")
def author_edits(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), author_edits_view)


@app.post("/api/author/gaps/{gap_id}")
def author_edit_gap(gap_id: str, body: DraftBody, session: Session = Depends(get_session)):
    return run_edit_gap(session, _world(body.world), gap_id, body.text, body.member_text)


@app.post("/api/author/gaps/{gap_id}/send")
def author_send_gap(gap_id: str, body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_send_gap(session, _world(body.world), gap_id)


@app.post("/api/author/units/{unit_id}")
def author_edit_unit(unit_id: str, body: DraftBody, session: Session = Depends(get_session)):
    return run_edit_returned(session, _world(body.world), unit_id, body.text, body.member_text)


@app.post("/api/author/units/{unit_id}/send")
def author_send_unit(unit_id: str, body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_send_returned(session, _world(body.world), unit_id)


@app.post("/api/author/drift/resolve")
def author_resolve_drift(body: DriftResolveBody, session: Session = Depends(get_session)):
    return run_resolve_drift(session, _world(body.world), body.note)


@app.post("/api/legal/decline")
def legal_decline(body: ReasonBody, session: Session = Depends(get_session)):
    return run_decline(session, _world(body.world), body.unit_id, body.reason)


@app.post("/api/conflicts/resolve")
def conflict_resolve(body: ConflictBody, session: Session = Depends(get_session)):
    return run_resolve(session, _world(body.world), body.conflict_id, body.reason)


@app.get("/api/search/prompts")
def prompts():
    return search_prompts()


@app.post("/api/search")
def search_post(body: SearchBody, session: Session = Depends(get_session)):
    from src.finish import canonical_role, resolve_explore_role

    world = _world(body.world)
    if world == "explore":
        if not session.explore_ready():
            raise APIError("Open an Explore role before using the sandbox.")
        role = resolve_explore_role(session, body.role)
    else:
        role = canonical_role(body.role)
    return run_search(session, world, role, body.query, body.record)


@app.post("/api/search/both")
def search_both(body: BothBody, session: Session = Depends(get_session)):
    return run_search_both(session, _world(body.world), body.query, body.record)


@app.get("/api/channels")
def channels_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), channels_view)


@app.post("/api/channels/publish")
def channels_publish(body: PublishBody = PublishBody(), session: Session = Depends(get_session)):
    return run_publish(session, _world(body.world), body.idempotency_key, body.text, body.member_text)


@app.get("/api/units/expired")
def units_expired(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), expired_view)


@app.get("/api/units")
def units_get(
    world: str = "guided",
    kb: str = "",
    status: str = "",
    type: str = "",
    q: str = "",
    role: str = "",
    latest: bool = True,
    session: Session = Depends(get_session),
):
    return _read(
        session,
        _world(world),
        lambda conn: units_view(conn, kb=kb, status=status, kind=type, q=q, role=role, latest=latest),
    )


@app.get("/api/units/{unit_id}")
def unit_get(unit_id: str, world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), lambda conn: unit_view(conn, unit_id))


@app.get("/api/units/{unit_id}/versions")
def versions_get(unit_id: str, world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), lambda conn: versions_view(conn, unit_id))


@app.get("/api/units/{unit_id}/as-of")
def as_of_get(unit_id: str, timestamp: str = "", world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), lambda conn: as_of_view(conn, unit_id, timestamp))


@app.get("/api/documents")
def documents_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), documents_view)


@app.get("/api/documents/{doc_id}")
def document_get(doc_id: str, world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), lambda conn: document_view(conn, doc_id))


@app.get("/api/gaps")
def gaps_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), gaps_view)


@app.post("/api/gaps/{gap_id}")
def gap_post(gap_id: str, body: GapBody, session: Session = Depends(get_session)):
    return run_gap(session, _world(body.world), gap_id, body.action, body.reason)


@app.get("/api/drift")
def drift_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), drift_view)


@app.post("/api/drift")
def drift_post(body: DriftBody, session: Session = Depends(get_session)):
    return run_drift(session, _world(body.world), body.kind)


@app.post("/api/drift/send")
def drift_send(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_drift_send(session, _world(body.world))


@app.get("/api/legal/drift")
def legal_drift(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), legal_drift_view)


@app.post("/api/legal/drift/approve")
def legal_drift_approve(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_approve_drift(session, _world(body.world))


@app.post("/api/legal/drift/return")
def legal_drift_return(body: DriftReturnBody, session: Session = Depends(get_session)):
    return run_return_drift(session, _world(body.world), body.reason)


@app.get("/api/evals")
def evals_get():
    """Scores from the latest eval run, written by scripts/run_evals.py. Read only; no session needed."""
    import json

    path = ROOT / "data" / "eval" / "results.json"
    if not path.exists():
        return {"available": False, "message": "No eval run has been scored yet.", "illustrative": True}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["available"] = True
    return data


@app.get("/api/quality")
def quality_get(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), quality_view)


@app.post("/api/quality/score")
def quality_score(body: WorldBody = WorldBody(), session: Session = Depends(get_session)):
    return run_score(session, _world(body.world))


@app.post("/api/feedback")
def feedback_post(body: FeedbackBody, session: Session = Depends(get_session)):
    return run_feedback(session, _world(body.world), body.model_dump())


@app.get("/api/feedback/author")
def feedback_author(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), feedback_author_view)


@app.get("/api/feedback/product")
def feedback_product(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), feedback_product_view)


@app.get("/api/feedback/open")
def feedback_open(route: str = "author", world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), lambda conn: feedback_open_view(conn, route))


@app.get("/api/feedback/summary")
def feedback_summary_route(world: str = "guided", session: Session = Depends(get_session)):
    return _read(session, _world(world), feedback_summary_view)


@app.post("/api/feedback/{feedback_id}/resolve")
def feedback_resolve(feedback_id: int, body: ResolveFeedbackBody, session: Session = Depends(get_session)):
    return run_resolve_feedback(session, _world(body.world), feedback_id, body.resolution)


@app.get("/api/activity")
def activity_get(world: str = "guided", limit: int = 12, session: Session = Depends(get_session)):
    return _read(session, _world(world), lambda conn: activity_view(conn, limit))


@app.get("/api/undo")
def undo_get(world: str = "guided", session: Session = Depends(get_session)):
    chosen = _world(world)
    with session._lock:
        return undo_payload(session, chosen)


@app.post("/api/undo")
def undo_post(body: UndoBody, session: Session = Depends(get_session)):
    return run_undo(session, _world(body.world), body.role, body.resource)


@app.post("/api/explore/open")
def explore_open(body: ExploreOpenBody, session: Session = Depends(get_session)):
    return open_explore(session, body.role)


@app.get("/api/explore")
def explore_get(session: Session = Depends(get_session)):
    with session._lock:
        return explore_view(session)


@app.post("/api/explore/page")
def explore_page(body: ExplorePageBody, session: Session = Depends(get_session)):
    return set_explore_page(session, body.page)


@app.post("/api/explore/reset")
def explore_reset(session: Session = Depends(get_session)):
    return reset_explore(session)


@app.post("/api/explore/ask")
def explore_ask_route(body: ExploreAskBody, session: Session = Depends(get_session)):
    return explore_ask(session, _bound_role(session, body.role), body.query, body.member_id, body.verified)


@app.get("/api/explore/questions")
def explore_questions(role: str = Query(...), session: Session = Depends(get_session)):
    return questions_view(_bound_role(session, role))


@app.get("/api/explore/calls")
def explore_calls(role: str = Query(...), session: Session = Depends(get_session)):
    return calls_view(_bound_role(session, role))


@app.post("/api/explore/desk")
def explore_desk(body: DeskBody, session: Session = Depends(get_session)):
    return desk_search(session, _bound_role(session, body.role), body.query, body.call_reason)


@app.post("/api/explore/verify")
def explore_verify(body: VerifyBody, session: Session = Depends(get_session)):
    from api.service import confirm_identifiers

    return confirm_identifiers(session, body.member_id, body.date_of_birth)


@app.post("/api/explore/phone/authenticate")
def explore_phone_auth(body: VerifyBody, session: Session = Depends(get_session)):
    from api.service import confirm_phone

    return confirm_phone(session, body.member_id, body.date_of_birth, body.call_id)


@app.post("/api/explore/member")
def explore_member(body: MemberBody, session: Session = Depends(get_session)):
    return member_turn(session, body.question, body.topic, body.member_id, body.channel, body.call_id)


@app.get("/api/explore/member/profile")
def explore_member_profile(member_id: str = "", session: Session = Depends(get_session)):
    from api.service import caller_verified

    verified = caller_verified(session, member_id)
    return _read(session, "explore", lambda conn: member_profile_view(conn, member_id, verified=verified))


@app.get("/api/explore/member/drug-price")
def explore_drug_price(
    member_id: str = "",
    drug_id: str = "",
    pharmacy: str = "preferred_retail",
    days: int = 30,
    session: Session = Depends(get_session),
):
    from api.plan_data import unverified_rule
    from api.service import caller_verified

    verified = caller_verified(session, member_id)

    def _price(conn):
        quote = drug_price_view(conn, member_id, drug_id, pharmacy, days)
        if verified:
            return quote
        rule = unverified_rule(conn)
        quote["available"] = False
        quote["price"] = None
        quote["price_display"] = ""
        quote["withheld_reason"] = rule["text"]
        quote["units"] = rule["units"]
        quote["verified"] = False
        return quote

    return _read(session, "explore", _price)


@app.get("/api/explore/member/visit-cost")
def explore_visit_cost(
    member_id: str = "",
    visit: str = "",
    network: str = "in",
    session: Session = Depends(get_session),
):
    from api.plan_data import unverified_rule
    from api.service import caller_verified

    verified = caller_verified(session, member_id)

    def _visit(conn):
        quote = visit_cost_view(conn, member_id, visit, network)
        if verified:
            return quote
        rule = unverified_rule(conn)
        quote["available"] = False
        quote["cost"] = None
        quote["cost_display"] = ""
        quote["withheld_reason"] = rule["text"]
        quote["units"] = rule["units"]
        quote["verified"] = False
        return quote

    return _read(session, "explore", _visit)


@app.get("/api/explore/member-record")
def explore_member_record(
    member_id: str = "",
    role: str = "",
    verified: bool = False,
    session: Session = Depends(get_session),
):
    from api.service import caller_verified

    del verified
    server_verified = caller_verified(session, member_id)
    return _read(
        session,
        "explore",
        lambda conn: member_record_view(conn, member_id, role, server_verified),
    )


@app.post("/api/explore/member/helped")
def explore_helped(body: HelpedBody, session: Session = Depends(get_session)):
    return member_helped(session, body.helped, body.question, body.unit_id)


@app.get("/api/explore/member/topics")
def explore_topics(session: Session = Depends(get_session)):
    return _read(session, "explore", member_topics_view)


@app.get("/api/explore/my-work")
def explore_work(session: Session = Depends(get_session)):
    if session.explore_ready():
        from src.finish import require_actor

        require_actor(session, "explore", ("Knowledge Ops author",))
    return _read(session, "explore", my_work_view)


@app.post("/api/author/documents/{doc_id}/units")
def author_add_unit(doc_id: str, body: AddUnitBody, session: Session = Depends(get_session)):
    from api.service import run_add_unit

    return run_add_unit(session, _world(body.world), doc_id, body.model_dump())


@app.post("/api/author/units/{unit_id}/review")
def author_unit_review(unit_id: str, body: ReviewBody, session: Session = Depends(get_session)):
    from api.service import run_unit_review

    return run_unit_review(session, _world(body.world), unit_id, body.model_dump())


@app.get("/api/author/documents")
def author_documents_route(world: str = "guided", all: bool = False, session: Session = Depends(get_session)):
    from api.present import author_documents_view
    from api.service import _sandbox_world

    chosen = _world(world)
    _sandbox_world(session, chosen, ("Knowledge Ops author",))
    return _read(session, chosen, lambda conn: author_documents_view(conn, include_all=all))


@app.get("/api/legal/documents")
def legal_documents_route(world: str = "guided", session: Session = Depends(get_session)):
    from api.present import legal_documents_view
    from api.service import _sandbox_world

    chosen = _world(world)
    _sandbox_world(session, chosen, ("Legal approver",))
    return _read(session, chosen, legal_documents_view)


@app.post("/api/author/gaps/{gap_id}/placeholders/{index}/source")
def placeholder_source(gap_id: str, index: int, body: PlaceholderSourceBody, session: Session = Depends(get_session)):
    from api.service import run_placeholder_source

    return run_placeholder_source(session, _world(body.world), gap_id, index, body.model_dump())


@app.post("/api/author/gaps/{gap_id}/placeholders/{index}/fill")
def placeholder_fill(gap_id: str, index: int, body: PlaceholderFillBody, session: Session = Depends(get_session)):
    from api.service import run_placeholder_fill

    return run_placeholder_fill(session, _world(body.world), gap_id, index, body.text)


@app.get("/api/explore/source-requests")
def source_requests_route(world: str = "explore", session: Session = Depends(get_session)):
    from api.present import source_requests_view
    from api.service import _sandbox_world

    chosen = _world(world, "explore")
    _sandbox_world(session, chosen, ("Knowledge Ops author",))
    return _read(session, chosen, source_requests_view)


@app.post("/api/explore/source-requests/{request_id}/answer")
def source_request_answer(request_id: str, body: SourceAnswerBody, session: Session = Depends(get_session)):
    from api.service import run_source_answer

    return run_source_answer(session, _world(body.world), request_id, body.statement, body.signer, body.no_policy)


@app.post("/api/author/gaps/{gap_id}/no-source")
def gap_no_source(gap_id: str, body: NoSourceBody, session: Session = Depends(get_session)):
    from api.service import run_gap_no_source

    return run_gap_no_source(session, _world(body.world), gap_id, body.reason)


@app.post("/api/author/gaps/{gap_id}/dismiss")
def gap_dismiss(gap_id: str, body: DismissBody, session: Session = Depends(get_session)):
    from api.service import run_gap_dismiss

    return run_gap_dismiss(session, _world(body.world), gap_id, body.kind, body.reason, body.unit_id)


@app.get("/api/legal/source-changes")
def legal_source_changes_route(world: str = "explore", session: Session = Depends(get_session)):
    from api.service import run_legal_source_changes

    return run_legal_source_changes(session, _world(world, "explore"))


@app.post("/api/legal/source-changes/{drift_id}")
def legal_source_change_act(drift_id: int, body: AuthorDriftActionBody, session: Session = Depends(get_session)):
    from api.service import run_legal_source_change

    return run_legal_source_change(session, _world(body.world), drift_id, body.action, body.reason, body.text)


@app.get("/api/author/drift")
def author_drift_route(world: str = "guided", session: Session = Depends(get_session)):
    from api.present import author_drift_list_view
    from api.service import _sandbox_world

    chosen = _world(world)
    _sandbox_world(session, chosen, ("Knowledge Ops author",))
    return _read(session, chosen, author_drift_list_view)


@app.post("/api/author/drift/{drift_id}")
def author_drift_action(drift_id: int, body: AuthorDriftActionBody, session: Session = Depends(get_session)):
    from api.service import run_author_drift

    return run_author_drift(session, _world(body.world), drift_id, body.action, body.reason, body.text)


@app.get("/api/explore/insights")
def explore_insights(session: Session = Depends(get_session)):
    return _read(session, "explore", insights_view)


@app.post("/api/explore/wrapup")
def explore_wrapup(body: WrapupBody, session: Session = Depends(get_session)):
    return run_wrapup(session, _world(body.world, "explore"), body.model_dump())


@app.get("/api/explore/wrapups")
def explore_wrapups(world: str = "explore", session: Session = Depends(get_session)):
    return _read(session, _world(world, "explore"), wrapups_view)


@app.get("/api/explore/changes")
def explore_changes(role: str = Query(...), world: str = "explore", session: Session = Depends(get_session)):
    chosen = _bound_role(session, role)
    return _read(session, _world(world, "explore"), lambda conn: changes_view(conn, chosen))


@app.post("/api/explore/changes/acknowledge")
def explore_acknowledge(body: AcknowledgeBody, session: Session = Depends(get_session)):
    return run_acknowledge(session, _world(body.world, "explore"), body.role, body.unit_id, body.version)


@app.get("/api/explore/scope")
def explore_scope(role: str = Query(...), session: Session = Depends(get_session)):
    return scope_view(_bound_role(session, role))


@app.get("/api/portal/quick-start")
def portal_quick(world: str = "explore", session: Session = Depends(get_session)):
    return _read(session, _world(world, "explore"), portal_quick_view)


@app.get("/api/portal/units")
def portal_units(world: str = "explore", knowledge_base: str = "", channel: str = "", session: Session = Depends(get_session)):
    return _read(
        session,
        _world(world, "explore"),
        lambda conn: portal_units_view(conn, knowledge_base, channel),
    )


@app.get("/api/portal/units/{unit_id}")
def portal_unit(unit_id: str, world: str = "explore", channel: str = "", session: Session = Depends(get_session)):
    return _read(session, _world(world, "explore"), lambda conn: portal_one_view(conn, unit_id, channel))


@app.get("/api/portal/events")
def portal_events(world: str = "explore", cursor: str = "", session: Session = Depends(get_session)):
    return _read(session, _world(world, "explore"), lambda conn: portal_events_view(conn, cursor))


@app.get("/api/portal/answers")
def portal_answers(
    question: str = "",
    role: str = "Pharmacy advocate",
    world: str = "explore",
    member_id: str = "",
    session: Session = Depends(get_session),
):
    """One cited answer for a channel. Member replies omit advocate text and unit ids."""
    return portal_answer(session, _world(world, "explore"), role, question, member_id)


def _static_file(full_path: str) -> FileResponse:
    if DIST.is_dir() and (DIST / "index.html").is_file():
        candidate = (DIST / full_path).resolve() if full_path else DIST / "index.html"
        try:
            candidate.relative_to(DIST.resolve())
        except ValueError:
            candidate = DIST / "index.html"
        if candidate.is_file():
            return FileResponse(candidate)
        index = DIST / "index.html"
        if index.is_file():
            return FileResponse(index)
    return FileResponse(PLACEHOLDER)


@app.post("/api/demo/units/{unit_id}/tags")
def unit_tags(unit_id: str, body: TagBody, session: Session = Depends(get_session)):
    from src.finish import save_tag_edit

    world = _world(body.world)
    actor = "Knowledge Ops author"
    with session._lock:
        with session.connection(world) as conn:
            save_tag_edit(
                conn,
                unit_id,
                body.audience,
                body.domain,
                ", ".join(body.tags),
                actor,
                world,
            )
    return {"ok": True, "unit_id": unit_id, "recorded": True, "illustrative": True}


@app.get("/api/legal/workload")
def legal_workload(world: str = "guided", session: Session = Depends(get_session)):
    from src.finish import workload

    return _read(session, _world(world), workload)


@app.post("/api/legal/review/extend")
def legal_extend(body: ReviewExtendBody, session: Session = Depends(get_session)):
    from src.finish import extend_review, require_actor

    world = _world(body.world, "explore")
    actor = require_actor(session, world, ("Legal approver",))
    with session._lock:
        with session.connection(world) as conn:
            note = extend_review(conn, body.unit_id, body.reason, body.review_by, actor)
    return {"ok": True, "message": note, "illustrative": True}


@app.post("/api/legal/review/retire")
def legal_retire(body: ReviewRetireBody, session: Session = Depends(get_session)):
    from src.finish import require_actor, retire_unit

    world = _world(body.world, "explore")
    actor = require_actor(session, world, ("Legal approver",))
    with session._lock:
        with session.connection(world) as conn:
            message = retire_unit(conn, body.unit_id, body.reason, actor)
    return {"ok": True, "message": message, "illustrative": True}


@app.get("/api/legal/link-reviews")
def legal_link_reviews(world: str = "guided", session: Session = Depends(get_session)):
    from src.finish import list_link_reviews

    return _read(session, _world(world), list_link_reviews)


@app.post("/api/legal/link-review/accept")
def legal_link_accept(body: ReviewRetireBody, session: Session = Depends(get_session)):
    from src.finish import accept_link_review, require_actor

    world = _world(body.world, "explore")
    actor = require_actor(session, world, ("Legal approver",))
    with session._lock:
        with session.connection(world) as conn:
            row = conn.execute(
                "SELECT id FROM link_reviews WHERE unit_id = ? AND status = 'sent' ORDER BY id DESC LIMIT 1",
                (body.unit_id,),
            ).fetchone()
            label = accept_link_review(conn, row["id"] if row is not None else None, actor)
    if not label:
        raise APIError("No linked review is waiting.")
    return {"ok": True, "message": label, "illustrative": True, "stays_live": True}


@app.post("/api/explore/member/authorized-caller")
def authorized_caller(body: CallerBody, session: Session = Depends(get_session)):
    from src.finish import store_authorized_caller

    if not session.explore_ready():
        raise APIError("Open an Explore role before using the sandbox.")
    with session._lock:
        with session.connection("explore") as conn:
            return store_authorized_caller(conn, body.member_id, body.caller_name, body.relationship)


@app.get("/api/explore/member/glossary")
def member_glossary(session: Session = Depends(get_session)):
    from src.finish import glossary_entries

    return _read(session, "explore", lambda conn: {"ok": True, "entries": glossary_entries(conn), "illustrative": True})


@app.post("/api/portal/webhooks")
def portal_webhooks(body: WebhookBody, session: Session = Depends(get_session)):
    from src.finish import register_webhook

    world = _world(body.world, "explore")
    with session._lock:
        with session.connection(world) as conn:
            return register_webhook(conn, body.url, body.events)


@app.get("/api/portal/openapi.json")
def portal_openapi():
    from src.finish import portal_openapi as spec

    return spec()


@app.get("/")
def home():
    return _static_file("")


@app.get("/{full_path:path}")
def spa(full_path: str):
    if full_path == "api" or full_path.startswith("api/") or full_path == "v1" or full_path.startswith("v1/"):
        return JSONResponse({"error": "That address is not part of the API."}, status_code=404)
    return _static_file(full_path)
