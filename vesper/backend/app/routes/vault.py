from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import bridge
from ..deps import require_auth

router = APIRouter()


class PathRequest(BaseModel):
    path: str


@router.get("/vault/list")
def vault_list(dir: str = "", _: None = Depends(require_auth)):
    try:
        return bridge.vault_list(dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/vault/delete")
def vault_delete(req: PathRequest, _: None = Depends(require_auth)):
    try:
        return bridge.vault_delete(req.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/vault/undo")
def vault_undo(_: None = Depends(require_auth)):
    return bridge.vault_undo()
