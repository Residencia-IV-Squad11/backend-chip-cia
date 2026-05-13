"""
config.py — Configuração central do Flask e do SQLAlchemy.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def create_app() -> Flask:
    app = Flask(__name__)

    # ── Segurança ──────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # ── Banco de Dados ─────────────────────────────────────────
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "chip_e_cia")

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://root:zbzH8DUmrf32UyBoF3QPIZmocKjhrozX@dpg-d726ocea2pns739kmt9g-a.oregon-postgres.render.com/chip_e_cia"
    )
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = os.getenv("FLASK_DEBUG", "False") == "True"

    # ── Extensões ──────────────────────────────────────────────
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Blueprints ─────────────────────────────────────────────
    from routes import atendimento_bp, dashboard_bp

    app.register_blueprint(atendimento_bp, url_prefix="/api/atendimento")
    app.register_blueprint(dashboard_bp,   url_prefix="/api/dashboard")

    return app
