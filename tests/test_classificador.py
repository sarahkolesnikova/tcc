import pytest

from residuos.dominio import CATEGORIAS, CATEGORIAS_SINIR, Destinacao, Familia
from residuos.transformacao.classificador import WasteClassifier

clf = WasteClassifier()

# As 23 descrições exatamente como aparecem na planilha SINIR do usuário.
LISTA_SINIR = [
    "Resíduos reutilizáveis ou recicláveis como agregados - Classe A",
    "Resíduos recicláveis para outras destinações - Classe B",
    "Resíduos para os quais não há reciclagem ou recuperação - Classe C",
    "Metal", "Papel/papelão", "Resíduos perfurocortantes ou escarificantes - Grupo E",
    "Orgânico", "Vidro", "Outros", "Plástico",
    "Resíduos perigosos oriundos do processo de construção - Classe D",
    "Resíduos do tratamento de esgoto", "Resíduos do tratamento de água",
    "Resíduos do manejo de águas pluviais", "Resíduos infectantes - Grupo A",
    "Resíduos contendo produtos químicos - Grupo B",
    "Resíduos que não apresentam risco biológico, químico ou radiológico - Grupo D",
    "Resíduos de portos", "Resíduos de aeroportos", "Resíduos de terminais alfandegários",
    "Resíduos de terminais rodoviários", "Resíduos de terminais ferroviários",
    "Resíduos de passagens de fronteira",
]


def test_catalogo_tem_23_categorias_sinir_e_ids_unicos():
    assert len(CATEGORIAS_SINIR) == 23
    assert len({c.id for c in CATEGORIAS}) == len(CATEGORIAS)


@pytest.mark.parametrize("descricao", LISTA_SINIR)
def test_cada_descricao_oficial_vira_sua_propria_categoria(descricao):
    cat = clf.classify(descricao)
    assert cat.id != "nc"
    assert cat.nome == descricao


def test_as_23_descricoes_mapeiam_para_23_categorias_distintas():
    assert len({clf.classify(d).id for d in LISTA_SINIR}) == 23


@pytest.mark.parametrize("texto,esperado", [
    ("RESIDUOS INFECTANTES - GRUPO A", "rssA"),          # caixa e acento
    ("Sucata de aço e alumínio", "metal"),
    ("Embalagens PET", "plastico"),
    ("Lodo de ETE", "esgoto"),
    ("Madeira, gesso e plásticos de obra - Classe B", "rccB"),  # classe vence 'plástico'
    ("Medicamentos - produtos químicos - Grupo B", "rssB"),
    ("Equipamentos eletroeletrônicos", "reee"),
    ("Pilhas e baterias", "reee"),
    ("Resíduos do porto de Santos", "portos"),
    ("Resíduos de aeroportos", "aero"),                   # 'porto' dentro de aeroporto não confunde
    ("", "nc"), (None, "nc"), ("xyz sem padrão", "nc"),
])
def test_textos_livres(texto, esperado):
    assert clf.classify(texto).id == esperado


@pytest.mark.parametrize("texto,destino,adequada", [
    ("Disposição Final em Aterro Sanitário", Destinacao.ATERRO_SANITARIO, True),
    ("Disposição Final em Lixão", Destinacao.LIXAO, False),
    ("Aterro controlado", Destinacao.ATERRO_CONTROLADO, False),
    ("Reciclagem", Destinacao.RECICLAGEM, True),
    ("Tratamento com aproveitamento energético", Destinacao.ENERGIA, True),
    ("Coprocessamento em fornos de cimento", Destinacao.COPROCESSAMENTO, True),
    (None, Destinacao.NAO_INFORMADA, True),
])
def test_destinacao(texto, destino, adequada):
    d = Destinacao.from_texto(texto)
    assert d is destino and d.adequada is adequada


def test_familias():
    assert clf.classify("Vidro").familia is Familia.RSU
    assert clf.classify("Resíduos de portos").familia is Familia.TRANSPORTE
