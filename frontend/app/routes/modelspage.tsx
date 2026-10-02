import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Aviso, Botao, Pagina } from "~/components/ui";
import { listarModelos } from "~/lib/api";
import { pct } from "~/lib/formato";
import { lerSessao, salvarSessao, type Sessao } from "~/lib/session";
import type { ModeloInfo, Modelos, TipoColuna } from "~/lib/types";

export function meta() {
  return [{ title: "Escolher modelos · Anomaly Detector" }];
}

const GRUPOS: { tipo: TipoColuna; titulo: string; colunas: (s: Sessao) => string[] }[] = [
  { tipo: "numeric", titulo: "Modelos numéricos", colunas: (s) => s.numeric_columns ?? [] },
  { tipo: "categorical", titulo: "Modelos categóricos", colunas: (s) => s.categorical_columns ?? [] },
];

export default function ModelsPage() {
  const navigate = useNavigate();
  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [modelos, setModelos] = useState<Modelos | null>(null);
  const [marcados, setMarcados] = useState<Set<string>>(new Set());
  const [contaminacao, setContaminacao] = useState(0.05);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const s = lerSessao();
    if (!s.arquivo) return void navigate("/upload", { replace: true });
    if (!s.numeric_columns?.length && !s.categorical_columns?.length) return void navigate("/decisions", { replace: true });
    setSessao(s);
    setContaminacao(s.threshold ?? 0.05);
    listarModelos().then((m) => {
      setModelos(m);
      const disponiveis = [...(s.numeric_columns?.length ? m.numeric : []), ...(s.categorical_columns?.length ? m.categorical : [])];
      const salvos = (s.models ?? []).filter((id) => disponiveis.some((d) => d.id === id));
      setMarcados(new Set(salvos.length ? salvos : disponiveis.map((d) => d.id)));
    }).catch((e) => setErro((e as Error).message));
  }, [navigate]);

  if (!sessao) return null;

  const alternar = (id: string) => setMarcados((a) => {
    const b = new Set(a);
    b.has(id) ? b.delete(id) : b.add(id);
    return b;
  });

  function gerar() {
    salvarSessao({ models: [...marcados], threshold: contaminacao });
    navigate("/report");
  }

  return (
    <Pagina etapa={2} titulo="Escolha os modelos"
      descricao="Cada modelo procura um tipo diferente de anomalia. Na dúvida, rode todos: o relatório mostra quantos modelos concordam sobre cada linha.">
      {erro && <Aviso>{erro}</Aviso>}

      <section className="flex max-w-3xl flex-col gap-3 rounded-lg border border-grade bg-folha p-5">
        <label htmlFor="contaminacao" className="font-bold">Fração de erros esperada (contaminação)</label>
        <p className="text-sm text-tinta-2">
          Quanto da planilha você acha que pode estar errado. Valores menores deixam os modelos mais rigorosos.
        </p>
        <div className="flex items-center gap-4">
          <input id="contaminacao" type="range" min={0.005} max={0.3} step={0.005} value={contaminacao}
            onChange={(e) => setContaminacao(Number(e.target.value))} className="w-full max-w-md accent-[var(--color-acao)]" />
          <output htmlFor="contaminacao" className="num w-16 text-right text-lg font-bold">{pct(contaminacao)}</output>
        </div>
      </section>

      {modelos && GRUPOS.map((g) => {
        const lista: ModeloInfo[] = modelos[g.tipo];
        const cols = g.colunas(sessao);
        const ativo = cols.length > 0;
        return (
          <section key={g.tipo} className="flex flex-col gap-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-xl font-bold">{g.titulo}</h2>
              {ativo ? (
                <button type="button" className="text-sm font-semibold text-acao hover:underline"
                  onClick={() => setMarcados((a) => {
                    const todos = lista.every((m) => a.has(m.id));
                    const b = new Set(a);
                    lista.forEach((m) => (todos ? b.delete(m.id) : b.add(m.id)));
                    return b;
                  })}>
                  {lista.every((m) => marcados.has(m.id)) ? "Desmarcar todos" : "Marcar todos"}
                </button>
              ) : (
                <span className="text-sm text-tinta-3">Nenhuma coluna {g.tipo === "numeric" ? "numérica" : "categórica"} selecionada</span>
              )}
            </div>
            {ativo && <p className="text-sm text-tinta-3">Colunas: {cols.join(", ")}</p>}
            <div className={`grid gap-3 sm:grid-cols-2 ${ativo ? "" : "opacity-50"}`}>
              {lista.map((m) => (
                <label key={m.id} htmlFor={`m-${m.id}`}
                  className={`flex gap-3 rounded-lg border bg-folha p-4 ${marcados.has(m.id) && ativo ? "border-acao" : "border-grade"} ${ativo ? "cursor-pointer" : ""}`}>
                  <input id={`m-${m.id}`} type="checkbox" disabled={!ativo} checked={ativo && marcados.has(m.id)}
                    onChange={() => alternar(m.id)} className="mt-1 size-4 shrink-0 accent-[var(--color-acao)]" />
                  <span className="flex flex-col gap-1">
                    <span className="font-semibold">{m.name}</span>
                    <span className="text-sm leading-snug text-tinta-2">{m.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </section>
        );
      })}

      <div className="flex flex-wrap items-center gap-4">
        <Botao onClick={gerar} disabled={!marcados.size}>Gerar relatório</Botao>
        <span className="text-sm text-tinta-3">{marcados.size} modelos selecionados</span>
      </div>
    </Pagina>
  );
}
