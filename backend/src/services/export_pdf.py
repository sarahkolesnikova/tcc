"""Relatório em PDF (ReportLab) para documentação formal de auditoria."""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TINTA = colors.HexColor("#1d2b36")
LINHA = colors.HexColor("#c9d1d6")
FUNDO = colors.HexColor("#eef2f4")


def _fmt(v, casas=3):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(v)


def _tabela(dados, larguras, cabecalho=True):
    t = Table(dados, colWidths=larguras, repeatRows=1 if cabecalho else 0)
    estilo = [("FONT", (0, 0), (-1, -1), "Helvetica", 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINHA), ("TEXTCOLOR", (0, 0), (-1, -1), TINTA)]
    if cabecalho:
        estilo += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("BACKGROUND", (0, 0), (-1, 0), FUNDO)]
    t.setStyle(TableStyle(estilo))
    return t


def gerar_pdf(rel: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title=f"Anomaly Detector — {rel['file']['filename']}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=16, textColor=TINTA, alignment=0)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, textColor=TINTA, spaceBefore=10)
    txt = ParagraphStyle("txt", parent=ss["BodyText"], fontSize=8.5, leading=11, textColor=TINTA)
    cel = ParagraphStyle("cel", parent=txt, fontSize=7.5, leading=9.5)
    P = lambda s, st=cel: Paragraph(escape(str(s)), st)  # noqa: E731

    f, par, s = rel["file"], rel["parameters"], rel["summary"]
    el = [Paragraph("Relatório de detecção de anomalias", h1),
          Paragraph(escape(f"Arquivo: {f['filename']} · {s['rows']:,} linhas · SHA-256 {f['sha256'][:16]}… · "
                           f"gerado em {datetime.now():%d/%m/%Y %H:%M}").replace(",", "."), txt),
          Paragraph(escape(f"Contaminação esperada: {par['threshold']:.1%} · colunas numéricas: "
                           f"{', '.join(par['numeric_columns']) or '—'} · categóricas: "
                           f"{', '.join(par['categorical_columns']) or '—'}"), txt),
          Spacer(1, 6),
          Paragraph(escape(f"{s['flagged_rows']} linhas sinalizadas por ao menos um modelo; "
                           f"{s['flagged_by_majority']} pela maioria dos {s['models_run']} modelos executados."), txt),
          Paragraph("Resumo por modelo", h2)]
    linhas = [["Modelo", "Tipo", "Anomalias", "Taxa", "Limiar", "Tempo (ms)"]]
    for m in rel["models"]:
        linhas.append([m["name"], "numérico" if m["type"] == "numeric" else "categórico", m["anomalies"],
                       f"{m['rate']:.1%}".replace(".", ","), _fmt(m["threshold"]), _fmt(m["elapsed_ms"], 1)])
    el.append(_tabela(linhas, [7 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 3 * cm, 3 * cm]))

    el.append(Paragraph("Registros sinalizados (ordenados por número de modelos e score de consenso)", h2))
    linhas = [["Linha", "Votos", "Consenso", "Valores", "Critérios"]]
    for r in rel["consensus"][:60]:
        valores = "; ".join(f"{k} = {v}" for k, v in r["values"].items())
        criterios = "\n".join(f"• {x['model']}: {x['reason']}" for x in r["reasons"])
        linhas.append([r["row"], r["votes"], _fmt(r["consensus_score"], 2), P(valores), P(criterios)])
    if len(linhas) == 1:
        linhas.append(["—", "—", "—", P("Nenhum registro sinalizado."), ""])
    el.append(_tabela(linhas, [1.4 * cm, 1.3 * cm, 1.8 * cm, 8 * cm, 14 * cm]))
    if len(rel["consensus"]) > 60:
        el.append(Paragraph(f"Mostrando 60 de {len(rel['consensus'])} registros; a lista completa está no CSV.", txt))

    est = rel["statistics"]
    if est["numeric"] or est["categorical"]:
        el += [PageBreak(), Paragraph("Estatísticas descritivas", h2)]
    if est["numeric"]:
        linhas = [["Coluna", "N", "Ausentes", "Média", "Desvio", "Mín", "Q1", "Mediana", "Q3", "Máx"]]
        for e in est["numeric"]:
            linhas.append([P(e["column"]), e["count"], e["missing"]] +
                          [_fmt(e[k], 2) for k in ("mean", "std", "min", "q1", "median", "q3", "max")])
        el.append(_tabela(linhas, [5 * cm] + [2.3 * cm] * 9))
    if est["categorical"]:
        el.append(Spacer(1, 8))
        linhas = [["Coluna", "N", "Distintos", "Mais frequente", "Freq.", "Ausentes"]]
        for e in est["categorical"]:
            linhas.append([P(e["column"]), e["count"], e["unique"], P(e["top"]), e["top_freq"], e["missing"]])
        el.append(_tabela(linhas, [6 * cm, 2.5 * cm, 2.5 * cm, 8 * cm, 2.5 * cm, 2.5 * cm]))

    el += [Spacer(1, 10), Paragraph(
        "Nota de método: os detectores são não supervisionados e indicam registros que fogem do padrão do "
        "próprio arquivo; uma sinalização é um candidato a revisão humana, não a confirmação de erro. "
        "Detectores univariados usam correção de Šidák para que a taxa de linhas sinalizadas fique próxima "
        "da contaminação informada.", txt)]

    def rodape(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(landscape(A4)[0] - 1.5 * cm, 0.8 * cm, f"Anomaly Detector · página {doc_.page}")
        canvas.restoreState()

    doc.build(el, onFirstPage=rodape, onLaterPages=rodape)
    return buf.getvalue()
