from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _problem(status: int, title: str, detail: str):
    return {"type": "about:blank", "status": status, "title": title, "detail": detail}


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content=_problem(400, "Bad Request", str(exc)))

    @app.exception_handler(KeyError)
    async def key_error_handler(_: Request, exc: KeyError):
        return JSONResponse(status_code=404, content=_problem(404, "Not Found", str(exc)))

    # Catch-all
    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        return JSONResponse(status_code=500, content=_problem(500, "Internal Server Error", str(exc)))
