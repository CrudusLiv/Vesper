# kernel/apps/web_app.py
from __future__ import annotations

import os
import threading

import uvicorn

from kernel.app import VesperApp
from kernel.web.server import create_app

_PORT = 8080


class WebApp(VesperApp):
    name = "web"
    version = "1.0"
    subscribes = []

    def on_start(self) -> None:
        password = os.environ.get("DASHBOARD_PASSWORD", "").strip()
        if not password:
            self.log("DASHBOARD_PASSWORD not set — dashboard disabled")
            return

        fastapi_app = create_app(
            data_dir=self.data,
            vault_dir=self.vault,
            password=password,
        )
        config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=_PORT, log_level="warning")
        server = uvicorn.Server(config)

        t = threading.Thread(target=server.run, daemon=True, name="dashboard-web")
        t.start()
        self.log(f"dashboard running on http://0.0.0.0:{_PORT}")
