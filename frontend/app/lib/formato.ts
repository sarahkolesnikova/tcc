const nf = (casas: number) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: casas });

export const numero = (v: number, casas = 2) => nf(casas).format(v);
export const pct = (v: number, casas = 1) =>
  new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: casas }).format(v);

export function bytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 ** 2) return `${numero(b / 1024, 1)} KB`;
  return `${numero(b / 1024 ** 2, 1)} MB`;
}

export function valor(v: string | number | null): string {
  if (v === null || v === undefined || v === "") return "vazio";
  return typeof v === "number" ? numero(v, 4) : v;
}
