import { Link } from "react-router";

const ETAPAS = [
  { to: "/upload", rotulo: "Enviar planilha" },
  { to: "/decisions", rotulo: "Escolher colunas" },
  { to: "/decisions/models", rotulo: "Escolher modelos" },
  { to: "/report", rotulo: "Relatório" },
];

/** Indicador do fluxo: a numeração é real, as etapas acontecem nesta ordem. */
export function Etapas({ atual }: { atual: number }) {
  return (
    <ol className="flex flex-wrap gap-x-6 gap-y-2 text-sm" aria-label="Etapas da análise">
      {ETAPAS.map((e, i) => {
        const estado = i < atual ? "feita" : i === atual ? "atual" : "futura";
        return (
          <li key={e.to} className="flex items-center gap-2" aria-current={estado === "atual" ? "step" : undefined}>
            <span className={`num grid size-6 place-items-center rounded-full text-xs font-bold ${
              estado === "atual" ? "bg-tinta text-folha" : estado === "feita" ? "bg-acao text-folha" : "border border-grade-forte text-tinta-3"}`}>
              {i + 1}
            </span>
            {estado === "feita" ? (
              <Link to={e.to} className="text-tinta-2 underline-offset-4 hover:underline">{e.rotulo}</Link>
            ) : (
              <span className={estado === "atual" ? "font-semibold" : "text-tinta-3"}>{e.rotulo}</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

type BotaoProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "primario" | "secundario" };

export function Botao({ variante = "primario", className = "", ...p }: BotaoProps) {
  const base = "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const cor = variante === "primario"
    ? "bg-acao text-folha hover:bg-acao-escura"
    : "border border-grade-forte bg-folha text-tinta hover:border-tinta";
  return <button className={`${base} ${cor} ${className}`} {...p} />;
}

export function Aviso({ children, tipo = "erro" }: { children: React.ReactNode; tipo?: "erro" | "info" }) {
  return (
    <div role={tipo === "erro" ? "alert" : "status"}
      className={`rounded-md border-l-4 px-4 py-3 text-sm ${tipo === "erro" ? "border-auditoria bg-auditoria-suave text-tinta" : "border-acao bg-folha text-tinta-2"}`}>
      {children}
    </div>
  );
}

export function Pagina({ etapa, titulo, descricao, children }: {
  etapa?: number; titulo: string; descricao?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-8">
      {etapa !== undefined && <Etapas atual={etapa} />}
      <header className="flex max-w-3xl flex-col gap-2">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{titulo}</h1>
        {descricao && <p className="text-base leading-relaxed text-tinta-2">{descricao}</p>}
      </header>
      {children}
    </div>
  );
}
