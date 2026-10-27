"""Ресурс «ссылка»: CRUD в /api/links и переход по короткой ссылке /r/…"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from shortener import repository
from shortener.db import get_session
from shortener.models import Link
from shortener.schemas import LinkCreate, LinkRead, LinkUpdate, ListParams

router = APIRouter(tags=["links"])

SessionDep = Annotated[Session, Depends(get_session)]


def to_read(link: Link, request: Request) -> LinkRead:
    base_url = request.app.state.settings.base_url
    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=f"{base_url}/r/{link.short_name}",
        created_at=link.created_at,
    )


def content_range(start: int, returned: int, total: int) -> str:
    """Значение Content-Range: реально отданные позиции, включительно."""
    if returned == 0:
        return f"links */{total}"
    return f"links {start}-{start + returned - 1}/{total}"


def get_link_or_404(session: Session, link_id: int) -> Link:
    link = repository.get_link(session, link_id)
    if link is None:
        raise HTTPException(
            status_code=404, detail=f"Ссылка с id={link_id} не найдена"
        )
    return link


def conflict(error: repository.ShortNameTaken) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=f"Короткое имя «{error.short_name}» уже занято",
    )


@router.get("/api/links", response_model=list[LinkRead])
def list_links(
    params: Annotated[ListParams, Query()],
    request: Request,
    response: Response,
    session: SessionDep,
):
    start, limit = 0, None
    if params.range is not None:
        start = params.range[0]
        limit = params.range[1] - params.range[0] + 1
    links = repository.list_links(
        session, offset=start, limit=limit, sort=params.sort or ("id", "ASC")
    )
    total = repository.count_links(session)
    response.headers["Content-Range"] = content_range(start, len(links), total)
    return [to_read(link, request) for link in links]


@router.post("/api/links", response_model=LinkRead, status_code=201)
def create_link(payload: LinkCreate, request: Request, session: SessionDep):
    try:
        link = repository.create_link(
            session, payload.original_url, payload.short_name
        )
    except repository.ShortNameTaken as error:
        raise conflict(error) from error
    return to_read(link, request)


@router.get("/api/links/{link_id}", response_model=LinkRead)
def get_link(link_id: int, request: Request, session: SessionDep):
    return to_read(get_link_or_404(session, link_id), request)


@router.put("/api/links/{link_id}", response_model=LinkRead)
def update_link(
    link_id: int, payload: LinkUpdate, request: Request, session: SessionDep
):
    link = get_link_or_404(session, link_id)
    try:
        link = repository.update_link(
            session, link, payload.original_url, payload.short_name
        )
    except repository.ShortNameTaken as error:
        raise conflict(error) from error
    return to_read(link, request)


@router.delete("/api/links/{link_id}", status_code=204)
def delete_link(link_id: int, session: SessionDep) -> Response:
    repository.delete_link(session, get_link_or_404(session, link_id))
    return Response(status_code=204)


@router.get("/r/{short_name}", status_code=302)
def follow_link(short_name: str, session: SessionDep) -> RedirectResponse:
    link = repository.find_by_short_name(session, short_name)
    if link is None:
        raise HTTPException(
            status_code=404,
            detail=f"Короткая ссылка «{short_name}» не найдена",
        )
    return RedirectResponse(link.original_url, status_code=302)
