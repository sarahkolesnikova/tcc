import { describe, expect, it } from "vitest";
import { colunasCitadas, corVotos } from "./destaque";

describe("colunasCitadas", () => {
  it("acha só nomes de colunas reais entre aspas", () => {
    const linha = {
      row: 1, votes: 2, consensus_score: 0.9, values: { valor: 25000, loja: "Centro" },
      reasons: [
        { model: "Z-Score", reason: "'valor' = 25000 está a 24 desvios-padrão" },
        { model: "Frequência", reason: "'loja' = 'Centro' aparece em 0,3%" },
      ],
    };
    expect([...colunasCitadas(linha)].sort()).toEqual(["loja", "valor"]);
  });
});

describe("corVotos", () => {
  it("separa nenhum voto, minoria e maioria", () => {
    expect(corVotos(0, 5)).toContain("grade");
    expect(corVotos(2, 5)).toContain("marca");
    expect(corVotos(3, 5)).toContain("auditoria");
  });
});
