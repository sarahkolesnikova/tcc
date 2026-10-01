"""Modelo de domínio: famílias, categorias SINIR, destinação e o registro de resíduo."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Familia(str, Enum):
    RCC = "RCC"
    RSU = "RSU"
    RSS = "RSS"
    SANEAMENTO = "Saneamento"
    TRANSPORTE = "Transporte"
    REEE = "REEE"
    NAO_CLASSIFICADO = "Não classificado"


class Destinacao(str, Enum):
    ATERRO_SANITARIO = "Aterro sanitário"
    ATERRO_CONTROLADO = "Aterro controlado"
    LIXAO = "Lixão"
    RECICLAGEM = "Reciclagem"
    COMPOSTAGEM = "Compostagem"
    ENERGIA = "Tratamento com aproveitamento energético"
    INCINERACAO = "Incineração"
    COPROCESSAMENTO = "Coprocessamento"
    TRATAMENTO = "Outro tratamento"
    NAO_INFORMADA = "Não informada"

    @property
    def adequada(self) -> bool:
        return self not in (Destinacao.LIXAO, Destinacao.ATERRO_CONTROLADO)

    @classmethod
    def from_texto(cls, texto: object) -> "Destinacao":
        """Normaliza o texto livre de destinação (Ibama/SINIR) para o enum."""
        from .transformacao.staging import norm  # import tardio evita ciclo

        t = norm(texto)
        if not t:
            return cls.NAO_INFORMADA
        regras = [
            (r"lixao|vazadouro|ceu aberto", cls.LIXAO),
            (r"aterro controlado", cls.ATERRO_CONTROLADO),
            (r"aterro", cls.ATERRO_SANITARIO),
            (r"recicl|reutiliz|recupera", cls.RECICLAGEM),
            (r"compost", cls.COMPOSTAGEM),
            (r"coprocess", cls.COPROCESSAMENTO),
            (r"energ|biogas|cdr", cls.ENERGIA),
            (r"incinera", cls.INCINERACAO),
            (r"tratamento|autoclave|esteriliza", cls.TRATAMENTO),
        ]
        for padrao, destino in regras:
            if re.search(padrao, t):
                return destino
        return cls.TRATAMENTO


@dataclass(frozen=True)
class Categoria:
    id: str
    familia: Familia
    nome: str
    palavras_chave: tuple[str, ...] = field(default=(), compare=False, repr=False)


# Ordem importa: padrões específicos (classe/grupo/terminal) antes dos genéricos.
CATEGORIAS: tuple[Categoria, ...] = (
    Categoria("rccA", Familia.RCC, "Resíduos reutilizáveis ou recicláveis como agregados - Classe A", ("classe a", "agregado")),
    Categoria("rccB", Familia.RCC, "Resíduos recicláveis para outras destinações - Classe B", ("classe b", "outras destina")),
    Categoria("rccC", Familia.RCC, "Resíduos para os quais não há reciclagem ou recuperação - Classe C", ("classe c", "nao ha reciclagem")),
    Categoria("rccD", Familia.RCC, "Resíduos perigosos oriundos do processo de construção - Classe D", ("classe d", "perigosos oriundos")),
    Categoria("rssA", Familia.RSS, "Resíduos infectantes - Grupo A", ("grupo a", "infectante")),
    Categoria("rssB", Familia.RSS, "Resíduos contendo produtos químicos - Grupo B", ("grupo b", "quimic")),
    Categoria("rssD", Familia.RSS, "Resíduos que não apresentam risco biológico, químico ou radiológico - Grupo D", ("grupo d", "nao apresentam risco")),
    Categoria("rssE", Familia.RSS, "Resíduos perfurocortantes ou escarificantes - Grupo E", ("grupo e", "perfurocortante", "escarificante")),
    Categoria("esgoto", Familia.SANEAMENTO, "Resíduos do tratamento de esgoto", ("esgoto", "lodo de ete")),
    Categoria("agua", Familia.SANEAMENTO, "Resíduos do tratamento de água", ("tratamento de agua", "lodo de eta")),
    Categoria("pluvial", Familia.SANEAMENTO, "Resíduos do manejo de águas pluviais", ("pluvia", "drenagem")),
    Categoria("alfa", Familia.TRANSPORTE, "Resíduos de terminais alfandegários", ("alfandeg",)),
    Categoria("rodo", Familia.TRANSPORTE, "Resíduos de terminais rodoviários", ("rodoviar",)),
    Categoria("ferro", Familia.TRANSPORTE, "Resíduos de terminais ferroviários", ("ferroviar",)),
    Categoria("fronteira", Familia.TRANSPORTE, "Resíduos de passagens de fronteira", ("fronteira",)),
    Categoria("aero", Familia.TRANSPORTE, "Resíduos de aeroportos", ("aeroporto",)),
    Categoria("portos", Familia.TRANSPORTE, "Resíduos de portos", (r"\bportos?\b",)),
    Categoria("reee", Familia.REEE, "Eletroeletrônicos, pilhas e lâmpadas (REEE)", ("eletroeletron", "eletronico", r"\breee\b", "pilha", "bateria", "lampada")),
    Categoria("metal", Familia.RSU, "Metal", ("metal", "sucata", "aluminio", r"\baco\b")),
    Categoria("papel", Familia.RSU, "Papel/papelão", ("papel",)),
    Categoria("vidro", Familia.RSU, "Vidro", ("vidro",)),
    Categoria("plastico", Familia.RSU, "Plástico", ("plastic", r"\bpet\b", "polietileno", "polimer")),
    Categoria("organico", Familia.RSU, "Orgânico", ("organic", "poda", "alimento")),
    Categoria("outros", Familia.RSU, "Outros", ("outros", "rejeito", "textil")),
)

NAO_CLASSIFICADO = Categoria("nc", Familia.NAO_CLASSIFICADO, "Não classificado")

#: As 23 categorias oficiais de caracterização do SINIR (sem REEE, que é recorte extra).
CATEGORIAS_SINIR = tuple(c for c in CATEGORIAS if c.familia is not Familia.REEE)


@dataclass(frozen=True)
class RegistroResiduo:
    uf: str
    ano: int | None
    massa_t: float
    categoria: Categoria
    destinacao: Destinacao

    @property
    def adequada(self) -> bool:
        return self.destinacao.adequada
