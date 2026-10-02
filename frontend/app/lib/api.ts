import type { Arquivo, Modelos, Parametros, Relatorio } from "./types";

export const API = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export class ErroApi extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function pedir<T>(caminho: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${API}${caminho}`, init);
  } catch {
    throw new ErroApi(0, `Não foi possível falar com o servidor em ${API}. Confira se o backend está rodando.`);
  }
  if (!r.ok) {
    let detalhe = r.statusText;
    try {
      const j = await r.json();
      detalhe = typeof j.detail === "string" ? j.detail : (j.detail?.[0]?.msg ?? detalhe);
    } catch {
      /* corpo não é JSON */
    }
    throw new ErroApi(r.status, detalhe);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

export function enviarArquivo(arquivo: File): Promise<Arquivo> {
  const form = new FormData();
  form.append("file", arquivo);
  return pedir<Arquivo>("/api/files/upload", { method: "POST", body: form });
}

export const obterArquivo = (id: string) => pedir<Arquivo>(`/api/files/${id}`);
export const listarModelos = () => pedir<Modelos>("/api/report/models");

export function gerarRelatorio(id: string, p: Parametros): Promise<Relatorio> {
  return pedir<Relatorio>(`/api/report/generate/${id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(p),
  });
}

export function urlExportacao(tipo: "cleaned" | "pdf", id: string, p: Parametros, remover = false): string {
  const q = new URLSearchParams({
    models: p.models.join(","),
    numeric_columns: p.numeric_columns.join(","),
    categorical_columns: p.categorical_columns.join(","),
    threshold: String(p.threshold),
  });
  if (remover) q.set("remover", "true");
  return `${API}/api/report/${tipo}/${id}?${q}`;
}
