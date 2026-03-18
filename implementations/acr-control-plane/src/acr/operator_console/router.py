from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from acr.common.operator_auth import OperatorPrincipal, get_operator_principal
from acr.config import settings

router = APIRouter(tags=["Console"])

_STATIC_DIR = Path(__file__).resolve().parent / "static"


if settings.acr_env == "development":

    @router.get("/console", response_class=HTMLResponse, include_in_schema=False)
    async def console_index() -> HTMLResponse:
        html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html)

else:

    @router.get("/console", response_class=HTMLResponse, include_in_schema=False)
    async def console_index(
        principal: OperatorPrincipal = Depends(get_operator_principal),
    ) -> HTMLResponse:
        html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html)



static_files = StaticFiles(directory=str(_STATIC_DIR), html=False)
