"""
app.py — Ponto de entrada da aplicação Flask.

Uso:
    python app.py              (modo desenvolvimento)
    flask run                  (modo desenvolvimento via CLI)
    gunicorn app:app           (produção)
"""

import logging
import os
from flask import send_from_directory
from sqlalchemy import inspect, text
from config import create_app, db

# ── Configuração de logging ────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if os.getenv("FLASK_DEBUG") == "True" else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Criação da aplicação ───────────────────────────────────────
app = create_app()


# ── Criação automática das tabelas (caso não existam) ──────────
with app.app_context():
    import models  # garante que todos os modelos são registrados
    db.create_all()

    inspector = inspect(db.engine)
    if "atendimento" in inspector.get_table_names():
        columns = [column_info["name"] for column_info in inspector.get_columns("atendimento")]
        if "external_id" not in columns:
            try:
                db.session.execute(text("ALTER TABLE atendimento ADD COLUMN external_id VARCHAR(128)"))
                db.session.commit()
                logging.getLogger(__name__).info("Coluna external_id adicionada à tabela atendimento.")
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Não foi possível criar a coluna external_id automaticamente: %s", exc
                )

    logging.getLogger(__name__).info("Tabelas verificadas/criadas com sucesso.")


# ── Rota de health-check ───────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "chip_e_cia API"}, 200


# ── Rotas para servir Frontend React ────────────────────────────
@app.route("/", methods=["GET"])
def serve_frontend():
    """Serve o index.html do React"""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:filename>", methods=["GET"])
def serve_static(filename):
    """Serve arquivos estáticos (CSS, JS, imagens)"""
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        # Se arquivo não existe, retorna o index.html (para SPA routing)
        return send_from_directory(app.static_folder, "index.html")


# ── Tratamento global de erros ─────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return {"sucesso": False, "erro": "Rota não encontrada."}, 404


@app.errorhandler(405)
def method_not_allowed(e):
    return {"sucesso": False, "erro": "Método HTTP não permitido nesta rota."}, 405


@app.errorhandler(500)
def internal_error(e):
    return {"sucesso": False, "erro": "Erro interno no servidor."}, 500


# ── Execução direta ────────────────────────────────────────────
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "True") == "True",
    )
