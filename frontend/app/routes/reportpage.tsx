import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { Aviso, Pagina } from "~/components/ui";
import { gerarRelatorio, urlExportacao } from "~/lib/api";
import { colunasCitadas, corVotos } from "~/lib/destaque";
import { numero, pct, valor } from "~/lib/formato";
import { lerSessao, parametrosDaSessao } from "~/lib/session";
import type { Parametros, Relatorio } from "~/lib/types";

export function meta() {
  return [{ title: "Relatório · Anomaly Detector" }];
}

const EIXO = { fontSize: 12, fill: "var(--color-tinta-2)" };
const DICA = {
  contentStyle: { background: "var(--color-folha)", border: "1px solid var(--color-grade)", borderRadius: 6, fontSize: 13 },
  labelStyle: { color: "var(--color-tinta)", fontWeight: 600 },
};
const POR_PAGINA = 25;

export default function ReportPage() {
  const navigate = useNavigate();
  const [params, setParams] = useState<Parametros | null>(null);
  const [fileId, setFileId] = useState<string>("");
  const [rel, setRel] = useState<Relatorio | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [pagina, setPagina] = useState(0);
  const [aberta, setAberta] = useState<number | null>(null);

  useEffect(() => {
    const s = lerSessao();
    const p = parametrosDaSessao(s);
    if (!s.arquivo || !p) return void navigate(s.arquivo ? "/decisions/models" : "/upload", { replace: true });
    setParams(p);
    setFileId(s.arquivo.file_id);
    gerarRelatorio(s.arquivo.file_id, p).then(setRel).catch((e) => setErro((e as Error).message));
  }, [navigate]);

  const totalModelos = rel?.summary.models_run ?? 0;
  const barras = useMemo(() => (rel?.models ?? []).map((m) => ({ nome: m.name, anomalias: m.anomalies, taxa: m.rate, tipo: m.type }))
    .sort((a, b) => b.anomalias - a.anomalias), [rel]);

  if (erro) {
    return (
      <Pagina etapa={3} titulo="Não foi possível gerar o relatório">
        <Aviso>{erro}</Aviso>
        <p className="text-sm"><Link to="/upload" className="font-semibold text-acao underline">Enviar a planilha de novo</Link> ou{" "}
          <Link to="/decisions/models" className="font-semibold text-acao underline">rever os modelos</Link>.</p>
      </Pagina>
    );
  }
  if (!rel || !params) {
    return (
      <Pagina etapa={3} titulo="Gerando relatório…" descricao="Os modelos estão analisando a planilha. Arquivos grandes podem levar alguns segundos.">
        <div className="h-2 w-64 overflow-hidden rounded bg-grade"><div className="h-full w-1/3 animate-pulse bg-acao" /></div>
      </Pagina>
    );
  }

  const { summary: s } = rel;
  const colunas = [...rel.parameters.numeric_columns, ...rel.parameters.categorical_columns];
  const linhas = rel.consensus.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA);
  const paginas = Math.ceil(rel.consensus.length / POR_PAGINA);

  return (
    <Pagina etapa={3} titulo={`Relatório de ${rel.file.filename}`}
      descricao={<>Contaminação esperada de {pct(rel.parameters.threshold)} · {totalModelos} modelos executados.
        Uma linha sinalizada é um candidato a revisão, não a confirmação de um erro.</>}>

      <section className="grid gap-px overflow-hidden rounded-lg border border-grade bg-grade sm:grid-cols-3" aria-label="Resumo">
        <Indicador valor={numero(s.rows, 0)} rotulo="linhas analisadas" />
        <Indicador valor={numero(s.flagged_rows, 0)} rotulo={`sinalizadas por ao menos um modelo (${pct(s.flagged_rows / s.rows)})`} />
        <Indicador valor={numero(s.flagged_by_majority, 0)} rotulo="sinalizadas pela maioria dos modelos" destaque />
      </section>

      <section className="flex flex-wrap gap-3" aria-label="Exportar">
        <a className="rounded-md bg-acao px-4 py-2.5 text-sm font-semibold text-folha hover:bg-acao-escura"
          href={urlExportacao("cleaned", fileId, params)} download>Baixar CSV com marcações</a>
        <a className="rounded-md border border-grade-forte bg-folha px-4 py-2.5 text-sm font-semibold hover:border-tinta"
          href={urlExportacao("cleaned", fileId, params, true)} download>Baixar CSV sem as linhas sinalizadas</a>
        <a className="rounded-md border border-grade-forte bg-folha px-4 py-2.5 text-sm font-semibold hover:border-tinta"
          href={urlExportacao("pdf", fileId, params)} download>Baixar PDF</a>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-bold">Linhas sinalizadas</h2>
        <p className="text-sm text-tinta-2">
          Ordenadas pelo número de modelos que concordam. As células destacadas são as citadas nos motivos:{" "}
          <span className="marca px-1">amarelo</span> quando a minoria dos modelos sinalizou,{" "}
          <span className="rounded bg-auditoria-suave px-1 text-auditoria">vermelho</span> quando foi a maioria.
          Clique numa linha para ver os motivos.
        </p>
        {rel.consensus.length === 0 ? (
          <Aviso tipo="info">Nenhuma linha foi sinalizada com esses modelos e essa contaminação.</Aviso>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-grade bg-folha">
            <table className="num w-full border-collapse text-sm" data-testid="tabela-consenso">
              <thead>
                <tr className="bg-papel text-left text-tinta-2">
                  <th className="border-b border-grade px-3 py-2 font-semibold">Linha</th>
                  <th className="border-b border-grade px-3 py-2 font-semibold">Modelos</th>
                  {colunas.map((c) => <th key={c} className="whitespace-nowrap border-b border-l border-grade px-3 py-2 font-semibold">{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {linhas.map((l) => {
                  const citadas = colunasCitadas(l);
                  const maioria = l.votes > totalModelos / 2;
                  const marca = maioria ? "rounded bg-auditoria-suave px-1 text-auditoria font-semibold" : "marca px-1";
                  return [
                    <tr key={l.row} onClick={() => setAberta(aberta === l.row ? null : l.row)}
                      className="cursor-pointer border-t border-grade hover:bg-papel" aria-expanded={aberta === l.row}>
                      <td className="px-3 py-2 font-semibold">{l.row}</td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-1.5">
                          <span className="size-2.5 rounded-full" style={{ background: corVotos(l.votes, totalModelos) }} />
                          {l.votes} de {totalModelos}
                        </span>
                      </td>
                      {colunas.map((c) => (
                        <td key={c} className="whitespace-nowrap border-l border-grade px-3 py-2">
                          <span className={citadas.has(c) ? marca : ""}>{valor(l.values[c])}</span>
                        </td>
                      ))}
                    </tr>,
                    aberta === l.row && (
                      <tr key={`${l.row}-motivos`} className="bg-papel">
                        <td colSpan={colunas.length + 2} className="px-4 py-3">
                          <ul className="flex flex-col gap-1.5 text-sm">
                            {l.reasons.map((r) => (
                              <li key={r.model}><b>{r.model}:</b> <span className="text-tinta-2">{r.reason}</span></li>
                            ))}
                          </ul>
                        </td>
                      </tr>
                    ),
                  ];
                })}
              </tbody>
            </table>
          </div>
        )}
        {paginas > 1 && (
          <div className="flex items-center gap-3 text-sm">
            <button type="button" disabled={pagina === 0} onClick={() => setPagina(pagina - 1)}
              className="rounded border border-grade bg-folha px-3 py-1.5 font-semibold disabled:opacity-40">Anterior</button>
            <span className="num text-tinta-2">Página {pagina + 1} de {paginas}</span>
            <button type="button" disabled={pagina >= paginas - 1} onClick={() => setPagina(pagina + 1)}
              className="rounded border border-grade bg-folha px-3 py-1.5 font-semibold disabled:opacity-40">Próxima</button>
          </div>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Grafico titulo="Anomalias por modelo" nota="Modelos que sinalizam muito acima da contaminação esperada tendem a ter mais falsos positivos.">
          <ResponsiveContainer width="100%" height={Math.max(220, barras.length * 30)}>
            <BarChart data={barras} layout="vertical" margin={{ left: 8, right: 24 }}>
              <CartesianGrid horizontal={false} stroke="var(--color-grade)" />
              <XAxis type="number" tick={EIXO} allowDecimals={false} />
              <YAxis type="category" dataKey="nome" width={170} tick={EIXO} />
              <Tooltip {...DICA} formatter={(v, _n, item) => [`${v} linhas (${pct((item.payload as { taxa: number }).taxa)})`, "Anomalias"]} />
              <Bar dataKey="anomalias" radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}>
                {barras.map((b) => <Cell key={b.nome} fill={b.tipo === "numeric" ? "var(--color-acao)" : "var(--color-tinta-2)"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="flex gap-4 text-xs text-tinta-2">
            <span className="inline-flex items-center gap-1.5"><i className="size-2.5 rounded-sm bg-acao" />numéricos</span>
            <span className="inline-flex items-center gap-1.5"><i className="size-2.5 rounded-sm bg-tinta-2" />categóricos</span>
          </p>
        </Grafico>

        <Grafico titulo="Quantos modelos concordam" nota="Linhas por número de modelos que as sinalizaram.">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={rel.votes_histogram.filter((h) => h.votes > 0)} margin={{ right: 16 }}>
              <CartesianGrid vertical={false} stroke="var(--color-grade)" />
              <XAxis dataKey="votes" tick={EIXO} label={{ value: "modelos", position: "insideBottom", offset: -2, ...EIXO }} />
              <YAxis tick={EIXO} allowDecimals={false} />
              <Tooltip {...DICA} labelFormatter={(v) => `${v} de ${totalModelos} modelos`} formatter={(v) => [`${v} linhas`, ""]} />
              <Bar dataKey="rows" radius={[4, 4, 0, 0]} maxBarSize={40} isAnimationActive={false}>
                {rel.votes_histogram.filter((h) => h.votes > 0).map((h) => <Cell key={h.votes} fill={corVotos(h.votes, totalModelos)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Grafico>

        {rel.scatter && (
          <Grafico titulo={`${rel.scatter.x} × ${rel.scatter.y}`} nota="Cada ponto é uma linha; a cor indica quantos modelos a sinalizaram." largo>
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ right: 16, bottom: 8 }}>
                <CartesianGrid stroke="var(--color-grade)" />
                <XAxis type="number" dataKey="x" name={rel.scatter.x} tick={EIXO} />
                <YAxis type="number" dataKey="y" name={rel.scatter.y} tick={EIXO} />
                <ZAxis range={[28, 28]} />
                <Tooltip {...DICA} cursor={{ strokeDasharray: "3 3" }}
                  formatter={(v, n) => [numero(Number(v), 4), n]} />
                <Scatter data={rel.scatter.points} isAnimationActive={false}>
                  {rel.scatter.points.map((p) => <Cell key={p.row} fill={corVotos(p.votes, totalModelos)}
                    stroke="var(--color-folha)" strokeWidth={p.votes ? 1 : 0} />)}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <p className="flex flex-wrap gap-4 text-xs text-tinta-2">
              <span className="inline-flex items-center gap-1.5"><i className="size-2.5 rounded-full" style={{ background: corVotos(0, 2) }} />não sinalizada</span>
              <span className="inline-flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-marca" />minoria dos modelos</span>
              <span className="inline-flex items-center gap-1.5"><i className="size-2.5 rounded-full bg-auditoria" />maioria dos modelos</span>
            </p>
          </Grafico>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-bold">Detalhes por modelo</h2>
        <div className="flex flex-col divide-y divide-grade rounded-lg border border-grade bg-folha">
          {rel.models.map((m) => (
            <details key={m.id} className="group px-4 py-3">
              <summary className="flex cursor-pointer flex-wrap items-baseline justify-between gap-2">
                <span className="font-semibold">{m.name}</span>
                <span className="num text-sm text-tinta-2">
                  {m.anomalies} {m.anomalies === 1 ? "linha" : "linhas"} ({pct(m.rate)}) · {numero(m.elapsed_ms, 1)} ms
                </span>
              </summary>
              {m.rows.length ? (
                <ul className="mt-3 flex max-h-72 flex-col gap-1 overflow-y-auto text-sm">
                  {m.rows.map((r) => (
                    <li key={r.row}><b className="num">Linha {r.row}:</b> <span className="text-tinta-2">{r.reason}</span></li>
                  ))}
                </ul>
              ) : <p className="mt-2 text-sm text-tinta-3">Nenhuma linha sinalizada por este modelo.</p>}
            </details>
          ))}
        </div>
      </section>

      {(rel.statistics.numeric.length > 0 || rel.statistics.categorical.length > 0) && (
        <section className="flex flex-col gap-3">
          <h2 className="text-xl font-bold">Estatísticas descritivas</h2>
          {rel.statistics.numeric.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-grade bg-folha">
              <table className="num w-full border-collapse text-sm">
                <thead><tr className="bg-papel text-left text-tinta-2">
                  {["Coluna", "Média", "Desvio", "Mín", "Q1", "Mediana", "Q3", "Máx", "Vazios"].map((h) => (
                    <th key={h} className={`px-3 py-2 font-semibold ${h === "Coluna" ? "" : "text-right"}`}>{h}</th>))}
                </tr></thead>
                <tbody>
                  {rel.statistics.numeric.map((e) => (
                    <tr key={e.column} className="border-t border-grade">
                      <td className="px-3 py-2 font-medium">{e.column}</td>
                      {[e.mean, e.std, e.min, e.q1, e.median, e.q3, e.max].map((v, i) => (
                        <td key={i} className="px-3 py-2 text-right">{numero(v)}</td>))}
                      <td className="px-3 py-2 text-right">{e.missing}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {rel.statistics.categorical.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-grade bg-folha">
              <table className="num w-full border-collapse text-sm">
                <thead><tr className="bg-papel text-left text-tinta-2">
                  {["Coluna", "Distintos", "Mais frequente", "Frequência", "Vazios"].map((h) => (
                    <th key={h} className="px-3 py-2 font-semibold">{h}</th>))}
                </tr></thead>
                <tbody>
                  {rel.statistics.categorical.map((e) => (
                    <tr key={e.column} className="border-t border-grade">
                      <td className="px-3 py-2 font-medium">{e.column}</td>
                      <td className="px-3 py-2">{e.unique}</td>
                      <td className="px-3 py-2">{e.top}</td>
                      <td className="px-3 py-2">{e.top_freq} ({pct(e.top_freq / e.count)})</td>
                      <td className="px-3 py-2">{e.missing}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </Pagina>
  );
}

function Indicador({ valor: v, rotulo, destaque }: { valor: string; rotulo: string; destaque?: boolean }) {
  return (
    <div className="flex flex-col gap-1 bg-folha px-5 py-4">
      <span className={`num text-3xl font-extrabold ${destaque ? "text-auditoria" : ""}`}>{v}</span>
      <span className="text-sm text-tinta-2">{rotulo}</span>
    </div>
  );
}

function Grafico({ titulo, nota, largo, children }: { titulo: string; nota: string; largo?: boolean; children: React.ReactNode }) {
  return (
    <figure className={`flex flex-col gap-3 rounded-lg border border-grade bg-folha p-5 ${largo ? "lg:col-span-2" : ""}`}>
      <figcaption className="flex flex-col gap-1">
        <span className="font-bold">{titulo}</span>
        <span className="text-sm text-tinta-2">{nota}</span>
      </figcaption>
      {children}
    </figure>
  );
}
