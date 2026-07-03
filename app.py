"""Vayu web application entry point.

Serves the dashboard (static) + JSON API. On first boot it seeds the bundled dataset
and, if configured, enriches it with live OpenAQ measurements.
"""
from __future__ import annotations

from flask import Flask, send_from_directory
from flask_cors import CORS

from vayu import config, seed, store
from vayu.api import api
from vayu.ingest import enrich_live


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="")
    CORS(app)
    app.register_blueprint(api)

    if not store.has_data():
        seed.generate()
        enrich_live()

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    print(f"Vayu running on http://{config.HOST}:{config.PORT}  (AI backend: {config.ai_backend()})")
    app.run(host=config.HOST, port=config.PORT, debug=False)
