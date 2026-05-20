"""
models.py — Modelos SQLAlchemy para o banco chip_e_cia.
Mapeia todas as tabelas do script SQL fornecido.
"""

from datetime import datetime
from config import db


# ──────────────────────────────────────────────
# TABELAS DE DOMÍNIO (lookup tables)
# ──────────────────────────────────────────────

class Categoria(db.Model):
    __tablename__ = "categoria"

    idcategoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome        = db.Column(db.String(100), nullable=False, unique=True)

    classificacoes = db.relationship("Classificacao", back_populates="categoria")

    def to_dict(self):
        return {"id": self.idcategoria, "nome": self.nome}


class Intencao(db.Model):
    __tablename__ = "intencao"

    idintencao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome       = db.Column(db.String(100), nullable=False, unique=True)

    classificacoes = db.relationship("Classificacao", back_populates="intencao")

    def to_dict(self):
        return {"id": self.idintencao, "nome": self.nome}


class Sentimento(db.Model):
    __tablename__ = "sentimento"

    idsentimento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome         = db.Column(db.String(50), nullable=False, unique=True)

    classificacoes = db.relationship("Classificacao", back_populates="sentimento")

    def to_dict(self):
        return {"id": self.idsentimento, "nome": self.nome}


class Criticidade(db.Model):
    __tablename__ = "criticidade"

    idcriticidade = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome          = db.Column(db.String(50), nullable=False, unique=True)
    nivel         = db.Column(db.Integer, nullable=False)

    classificacoes = db.relationship("Classificacao", back_populates="criticidade")

    def to_dict(self):
        return {"id": self.idcriticidade, "nome": self.nome, "nivel": self.nivel}


class Sla(db.Model):
    __tablename__ = "sla"

    idsla = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prazo = db.Column(db.String(50), nullable=False, unique=True)

    classificacoes = db.relationship("Classificacao", back_populates="sla")

    def to_dict(self):
        return {"id": self.idsla, "prazo": self.prazo}


class Topico(db.Model):
    __tablename__ = "topico"

    idtopico = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome     = db.Column(db.String(100), nullable=False, unique=True)

    def to_dict(self):
        return {"id": self.idtopico, "nome": self.nome}


# ──────────────────────────────────────────────
# TABELA DE ASSOCIAÇÃO N:N (atendimento_topico)
# ──────────────────────────────────────────────

atendimento_topico = db.Table(
    "atendimento_topico",
    db.Column(
        "atendimento_id",
        db.Integer,
        db.ForeignKey("atendimento.idatendimento", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "topico_id",
        db.Integer,
        db.ForeignKey("topico.idtopico", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ──────────────────────────────────────────────
# TABELAS PRINCIPAIS
# ──────────────────────────────────────────────

class Atendimento(db.Model):
    __tablename__ = "atendimento"

    idatendimento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    protocolo     = db.Column(db.String(100), unique=True, nullable=False)
    external_id   = db.Column(db.String(128), unique=True, nullable=True)
    texto         = db.Column(db.Text)
    resumo        = db.Column(db.Text)
    data_criacao  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamentos
    classificacao = db.relationship(
        "Classificacao", back_populates="atendimento", uselist=False, cascade="all, delete-orphan"
    )
    qualidade = db.relationship(
        "Qualidade", back_populates="atendimento", uselist=False, cascade="all, delete-orphan"
    )
    topicos = db.relationship(
        "Topico", secondary=atendimento_topico, backref="atendimentos"
    )

    def to_dict(self):
        return {
            "id":           self.idatendimento,
            "protocolo":    self.protocolo,
            "external_id":  self.external_id,
            "resumo":       self.resumo,
            "data_criacao": self.data_criacao.isoformat(),
            "classificacao": self.classificacao.to_dict() if self.classificacao else None,
            "qualidade":     self.qualidade.to_dict()     if self.qualidade     else None,
            "topicos":       [t.to_dict() for t in self.topicos],
        }


class Classificacao(db.Model):
    __tablename__ = "classificacao"

    idclassificacao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    atendimento_id  = db.Column(
        db.Integer, db.ForeignKey("atendimento.idatendimento", ondelete="CASCADE"), nullable=False
    )
    categoria_id    = db.Column(db.Integer, db.ForeignKey("categoria.idcategoria"),   nullable=False)
    intencao_id     = db.Column(db.Integer, db.ForeignKey("intencao.idintencao"),     nullable=False)
    sentimento_id   = db.Column(db.Integer, db.ForeignKey("sentimento.idsentimento"), nullable=False)
    criticidade_id  = db.Column(db.Integer, db.ForeignKey("criticidade.idcriticidade"), nullable=False)
    sla_id          = db.Column(db.Integer, db.ForeignKey("sla.idsla"),               nullable=False)

    # Relacionamentos
    atendimento = db.relationship("Atendimento", back_populates="classificacao")
    categoria   = db.relationship("Categoria",   back_populates="classificacoes")
    intencao    = db.relationship("Intencao",    back_populates="classificacoes")
    sentimento  = db.relationship("Sentimento",  back_populates="classificacoes")
    criticidade = db.relationship("Criticidade", back_populates="classificacoes")
    sla         = db.relationship("Sla",         back_populates="classificacoes")

    def to_dict(self):
        return {
            "categoria":   self.categoria.nome   if self.categoria   else None,
            "intencao":    self.intencao.nome     if self.intencao    else None,
            "sentimento":  self.sentimento.nome   if self.sentimento  else None,
            "criticidade": self.criticidade.nome  if self.criticidade else None,
            "sla":         self.sla.prazo         if self.sla         else None,
        }


class Qualidade(db.Model):
    __tablename__ = "qualidade"

    idqualidade      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    atendimento_id   = db.Column(
        db.Integer, db.ForeignKey("atendimento.idatendimento", ondelete="CASCADE"), nullable=False
    )
    empatia          = db.Column(db.Integer)
    clareza          = db.Column(db.Integer)
    objetividade     = db.Column(db.Integer)
    resolutividade   = db.Column(db.Integer)
    score_final      = db.Column(db.Numeric(4, 2))

    atendimento = db.relationship("Atendimento", back_populates="qualidade")

    def to_dict(self):
        return {
            "empatia":        self.empatia,
            "clareza":        self.clareza,
            "objetividade":   self.objetividade,
            "resolutividade": self.resolutividade,
            "score_final":    float(self.score_final) if self.score_final is not None else None,
        }
