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
    # Tenta variável de ambiente DATABASE_URL primeiro (para hospedagem)
    # Caso contrário, usa variáveis de banco relacionais ou SQLite local.
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    else:
        DB_TYPE = os.getenv("DB_TYPE")
        DB_USER = os.getenv("DB_USER")
        DB_PASS = os.getenv("DB_PASSWORD")
        DB_HOST = os.getenv("DB_HOST")
        DB_PORT = os.getenv("DB_PORT")
        DB_NAME = os.getenv("DB_NAME")

        if DB_TYPE and DB_USER and DB_PASS and DB_HOST and DB_PORT and DB_NAME:
            if DB_TYPE == "mysql+pymysql":
                app.config["SQLALCHEMY_DATABASE_URI"] = (
                    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
                )
            else:
                app.config["SQLALCHEMY_DATABASE_URI"] = (
                    f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
                )
        else:
            # Fallback para SQLite local se nenhuma configuração for fornecida
            app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chip_e_cia.db"
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
