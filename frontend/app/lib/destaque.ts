import type { LinhaConsenso } from "./types";

/** Colunas citadas entre aspas simples nos motivos de uma linha (as que devem ser destacadas). */
export function colunasCitadas(linha: LinhaConsenso): Set<string> {
  const nomes = new Set(Object.keys(linha.values));
  const out = new Set<string>();
  for (const { reason } of linha.reasons) {
    for (const m of reason.matchAll(/'([^']+)'/g)) if (nomes.has(m[1])) out.add(m[1]);
  }
  return out;
}

/** Cor do ponto/célula pelo número de modelos que concordam. */
export function corVotos(votos: number, total: number): string {
  if (votos === 0) return "var(--color-grade-forte)";
  if (votos > total / 2) return "var(--color-auditoria)";
  return "var(--color-marca)";
}
