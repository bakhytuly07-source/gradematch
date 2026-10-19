import logging
import os
from types import SimpleNamespace
from typing import Annotated

from fastapi import APIRouter, FastAPI, Request, Response, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.openapi.utils import get_openapi
from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartParser, MultiPartException
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool

from . import models, schemas
from .auth import Db, Token, hash_password, issue_token, verify_password
from .color import MAX_BYTES, analyze, build_lut, normalize_thumbnail
from .cube import write_cube
from .errors import ApiError
from .users import MemoryUsers
from .sessions import MemorySessions
from .looks import MemoryLooks

logger = logging.getLogger(__name__)
router = APIRouter()


async def api_error(request: Request, exc: ApiError):
    return JSONResponse({"code": exc.code, "message": exc.message}, status_code=exc.status)


async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse({"code": "validation", "message": "Invalid or missing request fields or settings."}, status_code=422)


async def http_error(request: Request, exc: HTTPException):
    code = "auth" if exc.status_code == 401 else "not_found" if exc.status_code == 404 else "validation"
    return JSONResponse({"code": code, "message": str(exc.detail)}, status_code=exc.status_code)


async def unexpected_error(request: Request, exc: Exception):
    # Do not log exception messages/tracebacks that may contain request secrets.
    logger.error("Unhandled API error (%s)", type(exc).__name__)
    return JSONResponse({"code": "unknown", "message": "Unexpected processing or server failure."}, status_code=500)


@router.post("/api/auth/register", response_model=schemas.AuthResult, status_code=201, operation_id="register")
def register(body: schemas.RegisterInput, db: Db, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        user = memory.users.create(body.email, body.password)
        return schemas.AuthResult(user=user.public(), access_token=memory.sessions.issue(user.id))
    user = models.User(email=body.email.strip().lower(), password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "An account with this email already exists.") from None
    return issue_token(db, user)


@router.post("/api/auth/login", response_model=schemas.AuthResult, operation_id="login")
def login(body: schemas.LoginInput, db: Db, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        user = memory.users.authenticate(body.email, body.password)
        if user is None:
            raise ApiError(401, "Email or password is incorrect.", "auth")
        return schemas.AuthResult(user=user.public(), access_token=memory.sessions.issue(user.id))
    user = db.scalar(select(models.User).where(models.User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "Email or password is incorrect.", "auth")
    return issue_token(db, user)


@router.post("/api/auth/logout", status_code=204, operation_id="logout")
def logout(db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        memory.sessions.revoke(token)
    else:
        db.delete(token)
        db.commit()
    return Response(status_code=204)


@router.get("/api/auth/me", response_model=schemas.User, operation_id="getMe")
def get_me(db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        user = memory.users.get(token.user_id)
        if user is None:
            raise ApiError(401, "Missing, expired or invalid bearer token.", "auth")
        return user.public()
    return db.get(models.User, token.user_id)


class MemoryMultipartParser(MultiPartParser):
    # The bounded stream below rejects oversized requests before this threshold.
    # Starlette's default 1MB spool would otherwise write uploaded originals to disk.
    spool_max_size = MAX_BYTES + 1024 * 1024 + 1
    complete = False

    def on_part_begin(self):
        super().on_part_begin()
        self.file_bytes = 0

    def on_part_data(self, data, start, end):
        if self._current_part.file is not None:
            self.file_bytes += end - start
            if self.file_bytes > MAX_BYTES:
                raise MultiPartException("too_large")
        super().on_part_data(data, start, end)

    def on_end(self):
        self.complete = True


@router.post("/api/generate", response_model=schemas.StyleParams, operation_id="generateLook", openapi_extra={
    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["referenceFile"], "properties": {
            "referenceFile": {"type": "string", "format": "binary"}}}}}}})
async def generate(request: Request):
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "multipart/form-data":
        raise ApiError(422, "Missing or malformed referenceFile upload.")
    async def bounded_stream():
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > MAX_BYTES + 1024 * 1024:
                # MultiPartException makes Starlette close partial upload handles.
                raise MultiPartException("too_large")
            yield chunk
    parser = MemoryMultipartParser(request.headers, bounded_stream(), max_files=1, max_fields=0)
    try:
        form = await parser.parse()
    except (MultiPartException, MultipartParseError, ValueError) as exc:
        # MultipartParseError can bypass Starlette's MultiPartException cleanup.
        for file in parser._files_to_close_on_error:
            file.close()
        if str(exc) == "too_large":
            raise ApiError(413, "Reference image exceeds 15 MB.") from None
        raise ApiError(422, "Missing or malformed referenceFile upload.") from None
    try:
        if not parser.complete:
            raise ApiError(422, "Incomplete multipart upload.")
        upload = form.get("referenceFile")
        if not isinstance(upload, UploadFile):
            raise ApiError(422, "Missing referenceFile upload.")
        data = await upload.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ApiError(413, "Reference image exceeds 15 MB.")
        return await run_in_threadpool(analyze, data)
    finally:
        await form.close()
        # Incomplete parts may have a handle without an entry in FormData.
        for file in parser._files_to_close_on_error:
            file.close()


@router.post("/api/render-lut", response_model=schemas.LutData, operation_id="renderLut")
def render_lut(body: schemas.LutSettings):
    return {"size": 33, "data": build_lut(body).ravel().tolist()}


@router.post("/api/download.cube", response_class=PlainTextResponse, operation_id="downloadLutCube")
def download_cube(body: schemas.LutSettings):
    return PlainTextResponse(write_cube(build_lut(body)), headers={"Content-Disposition": 'attachment; filename="gradematch-look.cube"'})


def own_look(id: str, db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        return memory.looks.get(token.user_id, id)
    look = db.scalar(select(models.Look).where(models.Look.id == id, models.Look.user_id == token.user_id))
    if look is None:
        raise ApiError(404, "Look was not found.", "not_found")
    return look


OwnLook = Annotated[models.Look, Depends(own_look)]


@router.post("/api/looks", response_model=schemas.Look, status_code=201, operation_id="saveLook")
def save_look(body: schemas.SaveLookInput, db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        return memory.looks.create(token.user_id, body)
    timestamp = models.now_ms()
    look = models.Look(user_id=token.user_id, name=body.name.strip() or "Untitled look",
                       style_params=body.style_params.model_dump(by_alias=True),
                       adjustments=body.adjustments.model_dump(), thumbnail_url=normalize_thumbnail(body.thumbnail),
                       is_favorite=False, created_at=timestamp, updated_at=timestamp)
    db.add(look)
    db.commit()
    return look


@router.get("/api/looks", response_model=list[schemas.Look], operation_id="listLooks")
def list_looks(db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        return memory.looks.for_owner(token.user_id)
    return db.scalars(select(models.Look).where(models.Look.user_id == token.user_id)
                      .order_by(models.Look.created_at.desc(), models.Look.id.desc())).all()


@router.get("/api/looks/{id}", response_model=schemas.Look, operation_id="getLook")
def get_look(look: OwnLook):
    return look


@router.patch("/api/looks/{id}", response_model=schemas.Look, operation_id="renameLook")
def rename_look(body: schemas.RenameLookInput, look: OwnLook, db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        return memory.looks.rename(token.user_id, look.id, body.name)
    look.name = body.name.strip()
    look.updated_at = max(models.now_ms(), look.updated_at + 1)
    db.commit()
    return look


@router.post("/api/looks/{id}/favorite", response_model=schemas.Look, operation_id="toggleFavorite")
def toggle_favorite(look: OwnLook, db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        return memory.looks.toggle_favorite(token.user_id, look.id)
    timestamp = models.now_ms()
    db.execute(update(models.Look).where(models.Look.id == look.id, models.Look.user_id == look.user_id)
               .values(is_favorite=~models.Look.is_favorite,
                       updated_at=case((models.Look.updated_at >= timestamp, models.Look.updated_at + 1),
                                       else_=timestamp)),
               execution_options={"synchronize_session": False})
    db.commit()
    db.refresh(look)
    return look


@router.delete("/api/looks/{id}", status_code=204, operation_id="deleteLook")
def delete_look(look: OwnLook, db: Db, token: Token, request: Request):
    memory = request.app.state.memory
    if memory is not None:
        memory.looks.delete(token.user_id, look.id)
    else:
        db.delete(look)
        db.commit()
    return Response(status_code=204)


# FastAPI otherwise documents its default HTTPValidationError even though our
# handlers return the contract's Error shape. Keep interactive docs accurate.
def contract_openapi(app: FastAPI):
    if app.openapi_schema is not None:
        return app.openapi_schema
    document = get_openapi(title=app.title, version=app.version, routes=app.routes)
    document["components"]["schemas"]["Error"] = schemas.Error.model_json_schema()
    statuses = {
        "register": [422, 409, 500], "login": [422, 401, 500],
        "logout": [401, 500], "getMe": [401, 500],
        "generateLook": [413, 415, 422, 500], "renderLut": [422, 500],
        "downloadLutCube": [422, 500], "saveLook": [401, 422, 500],
        "listLooks": [401, 500], "getLook": [401, 404, 500],
        "renameLook": [401, 404, 422, 500], "deleteLook": [401, 404, 500],
        "toggleFavorite": [401, 404, 500],
    }
    for item in document["paths"].values():
        for operation in item.values():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            operation["responses"].pop("422", None)
            for status in statuses[operation["operationId"]]:
                operation["responses"][str(status)] = {
                    "description": "Request failed; see code and message.",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
                }
            operation.setdefault("security", [])
    app.openapi_schema = document
    return document


def create_app(*, storage="memory", users=None, sessions=None, looks=None):
    if storage not in {"memory", "orm"}:
        raise ValueError("storage must be memory or orm")
    application = FastAPI(title="GradeMatch API", version="1.0.0")
    application.state.memory = (SimpleNamespace(
        users=users if users is not None else MemoryUsers(),
        sessions=sessions if sessions is not None else MemorySessions(),
        looks=looks if looks is not None else MemoryLooks(),
    ) if storage == "memory" else None)
    application.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"], expose_headers=["Content-Disposition"])
    for error, handler in [(ApiError, api_error), (RequestValidationError, validation_error),
                           (HTTPException, http_error), (Exception, unexpected_error)]:
        application.add_exception_handler(error, handler)
    application.include_router(router)
    application.openapi = lambda: contract_openapi(application)
    return application


app = create_app(storage=os.getenv("GRADEMATCH_STORAGE", "memory"))
