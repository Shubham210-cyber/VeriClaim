import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.db.session import SessionLocal, init_db
from app.errors import AppError
from app.policies.catalog import seed_policies

log = logging.getLogger("claimproof")


def create_app() -> FastAPI:
    app = FastAPI(title="ClaimProof (VeriClaim) API", version="0.1.0",
                  description="Evidence-based claim review. Reviewer decision support only.")
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=["*"],
                       allow_headers=["*"])

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        with SessionLocal() as db:
            seed_policies(db)

    @app.exception_handler(AppError)
    async def _app_error(_: Request, e: AppError):
        return JSONResponse({"error": {"code": e.code, "message": e.message}}, status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        fields = ", ".join(".".join(str(p) for p in err["loc"][1:]) for err in e.errors())
        return JSONResponse({"error": {"code": "VALIDATION_ERROR", "message": f"Invalid request: {fields}"}}, status_code=422)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, e: Exception):
        log.exception("unhandled error")
        return JSONResponse({"error": {"code": "INTERNAL_ERROR", "message": "Something went wrong."}}, status_code=500)

    @app.get("/health")
    def health():
        return {"status": "ok", "ai_provider": settings.ai_provider if settings.ai_enabled else "none"}

    app.include_router(router)
    return app


app = create_app()
