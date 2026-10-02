// Estado do fluxo entre as rotas, guardado no LocalStorage (decisão do TCC: sem gerenciador global).
import type { Arquivo, Parametros } from "./types";

const CHAVE = "anomaly-detector:sessao";

export interface Sessao {
  arquivo?: Arquivo;
  numeric_columns?: string[];
  categorical_columns?: string[];
  models?: string[];
  threshold?: number;
}

export function lerSessao(): Sessao {
  try {
    return JSON.parse(localStorage.getItem(CHAVE) ?? "{}") as Sessao;
  } catch {
    return {};
  }
}

export function salvarSessao(parcial: Partial<Sessao>): Sessao {
  const nova = { ...lerSessao(), ...parcial };
  try {
    localStorage.setItem(CHAVE, JSON.stringify(nova));
  } catch {
    /* navegação privada sem armazenamento: o fluxo segue na memória da página */
  }
  return nova;
}

export function limparSessao() {
  try {
    localStorage.removeItem(CHAVE);
  } catch {
    /* sem armazenamento disponível */
  }
}

export function parametrosDaSessao(s: Sessao): Parametros | null {
  if (!s.arquivo || !s.models?.length) return null;
  return {
    models: s.models,
    numeric_columns: s.numeric_columns ?? [],
    categorical_columns: s.categorical_columns ?? [],
    threshold: s.threshold ?? 0.05,
  };
}
