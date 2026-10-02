import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { Aviso, Botao, Pagina } from "~/components/ui";
import { obterArquivo } from "~/lib/api";
import { bytes, numero } from "~/lib/formato";
import { lerSessao, salvarSessao } from "~/lib/session";
import type { Arquivo, TipoColuna } from "~/lib/types";

export function meta() {
  return [{ title: "Escolher colunas · Anomaly Detector" }];
}

type Escolha = { usar: boolean; tipo: TipoColuna };

export default function FilterColumns() {
  const navigate = useNavigate();
  const [arquivo, setArquivo] = useState<Arquivo | null>(null);
  const [escolhas, setEscolhas] = useState<Record<string, Escolha>>({});
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const s = lerSessao();
    if (!s.arquivo) {
      navigate("/upload", { replace: true });
      return;
    }
    setArquivo(s.arquivo);
    const ja = new Set([...(s.numeric_columns ?? []), ...(s.categorical_columns ?? [])]);
    const inicial: Record<string, Escolha> = {};
    for (const c of s.arquivo.columns) {
      const tipoSalvo: TipoColuna | undefined = s.numeric_columns?.includes(c.name) ? "numeric"
        : s.categorical_columns?.includes(c.name) ? "categorical" : undefined;
      // por padrão, ignora colunas que parecem identificadores (um valor diferente por linha)
      const pareceId = c.type === "categorical" && c.unique === s.arquivo.rows;
      inicial[c.name] = { usar: ja.size ? ja.has(c.name) : !pareceId, tipo: tipoSalvo ?? c.type };
    }
    setEscolhas(inicial);
    obterArquivo(s.arquivo.file_id).catch((e) => setErro((e as Error).message));
  }, [navigate]);

  if (!arquivo) return null;
  const selecionadas = Object.entries(escolhas).filter(([, e]) => e.usar);

  function continuar() {
    salvarSessao({
      numeric_columns: selecionadas.filter(([, e]) => e.tipo === "numeric").map(([n]) => n),
      categorical_columns: selecionadas.filter(([, e]) => e.tipo === "categorical").map(([n]) => n),
    });
    navigate("/decisions/models");
  }

  const alterar = (nome: string, parcial: Partial<Escolha>) =>
    setEscolhas((a) => ({ ...a, [nome]: { ...a[nome], ...parcial } }));

  return (
    <Pagina etapa={1} titulo="Escolha as colunas"
      descricao={<>
        <b className="text-tinta">{arquivo.filename}</b> · <span className="num">{numero(arquivo.rows, 0)}</span> linhas ·{" "}
        <span className="num">{bytes(arquivo.size_bytes)}</span>. O tipo de cada coluna foi detectado automaticamente;
        corrija se precisar. Colunas de código ou identificador costumam atrapalhar a análise.
      </>}>
      {erro && (
        <Aviso>{erro} <Link to="/upload" className="font-semibold underline">Enviar de novo</Link></Aviso>
      )}
      <div className="overflow-x-auto rounded-lg border border-grade bg-folha">
        <table className="num w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr className="bg-papel text-left text-tinta-2">
              <th className="px-4 py-2 font-semibold">Analisar</th>
              <th className="px-4 py-2 font-semibold">Coluna</th>
              <th className="px-4 py-2 font-semibold">Tipo</th>
              <th className="px-4 py-2 text-right font-semibold">Valores distintos</th>
              <th className="px-4 py-2 text-right font-semibold">Vazios</th>
            </tr>
          </thead>
          <tbody>
            {arquivo.columns.map((c, i) => {
              const e = escolhas[c.name];
              if (!e) return null;
              return (
                <tr key={c.name} className="border-t border-grade">
                  <td className="px-4 py-2">
                    <input id={`usar-${i}`} type="checkbox" className="size-4 accent-[var(--color-acao)]"
                      checked={e.usar} onChange={(ev) => alterar(c.name, { usar: ev.target.checked })} />
                  </td>
                  <td className="px-4 py-2 font-medium"><label htmlFor={`usar-${i}`}>{c.name}</label></td>
                  <td className="px-4 py-2">
                    <select aria-label={`Tipo de ${c.name}`} value={e.tipo}
                      onChange={(ev) => alterar(c.name, { tipo: ev.target.value as TipoColuna })}
                      className="rounded border border-grade bg-folha px-2 py-1">
                      <option value="numeric">Numérica</option>
                      <option value="categorical">Categórica</option>
                    </select>
                  </td>
                  <td className="px-4 py-2 text-right">{numero(c.unique, 0)}</td>
                  <td className="px-4 py-2 text-right">{numero(c.missing, 0)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <Botao onClick={continuar} disabled={!selecionadas.length || !!erro}>Continuar para os modelos</Botao>
        <span className="text-sm text-tinta-3">{selecionadas.length} de {arquivo.columns.length} colunas selecionadas</span>
      </div>
    </Pagina>
  );
}
