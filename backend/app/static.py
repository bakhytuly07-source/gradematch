"""Optional frontend hosting, registered after the API and documentation routes."""
import os
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        # Never turn missing API/asset requests into successful HTML responses.
        if path.split("/", 1)[0] in {"api", "assets", "docs", "redoc", "openapi.json"}:
            return await super().get_response(path, scope) if path.startswith("assets/") else self.not_found()
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or Path(path).suffix:
                raise
            # StaticFiles performs containment checks (including symlinks) for
            # both real files and the shell. No user path is joined manually.
            return await super().get_response("_shell.html", scope)

    @staticmethod
    def not_found():
        raise HTTPException(status_code=404)


def mount_frontend(app):
    directory = os.getenv("STATIC_DIR")
    if directory and Path(directory).is_dir():
        app.mount("/", FrontendFiles(directory=directory), name="frontend")
