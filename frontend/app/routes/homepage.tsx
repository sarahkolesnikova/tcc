import { Link } from "react-router";

export function meta() {
  return [{ title: "Anomaly Detector" },
    { name: "description", content: "Encontre registros fora do padrão em planilhas CSV, XLSX e XLS." }];
}

// Amostra ilustrativa da planilha: as células marcadas são o que o sistema aponta.
const AMOSTRA = [
  ["412", "Centro", "pix", "1.020,40", ""],
  ["413", "Norte", "cartão", "987,10", ""],
  ["414", "Centro", "pix", "25.000,00", "valor"],
  ["415", "Lojaa Centro", "cartão", "1.104,90", "loja"],
  ["416", "Sul", "pix", "943,75", ""],
];

const PASSOS = [
  ["Envie a planilha", "CSV, XLSX ou XLS de até 50 MB. Arquivos brasileiros com ponto e vírgula e vírgula decimal são lidos direto."],
  ["Escolha as colunas", "O sistema separa colunas numéricas e categóricas; você marca as que fazem sentido analisar."],
  ["Escolha os modelos", "Até 14 detectores. Informe a fração de erros que espera encontrar (contaminação)."],
  ["Leia o relatório", "Cada linha sinalizada vem com o motivo. Exporte em CSV para corrigir ou em PDF para documentar."],
];

export default function Homepage() {
  return (
    <div className="flex flex-col gap-16">
      <section className="grid items-center gap-10 lg:grid-cols-[1.05fr_1fr]">
        <div className="flex flex-col gap-5">
          <h1 className="text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl">
            Encontre os registros fora do padrão na sua planilha
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-tinta-2">
            O Anomaly Detector combina métodos estatísticos e aprendizado de máquina para apontar valores
            e combinações suspeitas, e explica por que cada linha foi sinalizada. Não precisa programar.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/upload" className="rounded-md bg-acao px-5 py-3 font-semibold text-folha hover:bg-acao-escura">
              Analisar uma planilha
            </Link>
            <a href="#como-usar" className="rounded-md border border-grade-forte bg-folha px-5 py-3 font-semibold hover:border-tinta">
              Ver como funciona
            </a>
          </div>
        </div>

        <figure className="overflow-x-auto rounded-lg border border-grade bg-folha shadow-[0_1px_0_var(--color-grade)]">
          <table className="num w-full min-w-[26rem] border-collapse text-sm">
            <thead>
              <tr className="bg-papel text-left text-tinta-2">
                {["linha", "loja", "pagamento", "valor (R$)"].map((h) => (
                  <th key={h} className="border-b border-r border-grade px-3 py-2 font-semibold last:border-r-0">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {AMOSTRA.map(([linha, loja, pag, valor, marca]) => (
                <tr key={linha}>
                  <td className="border-b border-r border-grade px-3 py-2 text-tinta-3">{linha}</td>
                  <td className="border-b border-r border-grade px-3 py-2">
                    <span className={marca === "loja" ? "marca risca px-1" : ""}>{loja}</span>
                  </td>
                  <td className="border-b border-r border-grade px-3 py-2">{pag}</td>
                  <td className="border-b border-grade px-3 py-2 text-right">
                    <span className={marca === "valor" ? "marca risca px-1" : ""}>{valor}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <figcaption className="flex flex-col gap-1 border-t border-grade px-3 py-3 text-xs leading-relaxed text-tinta-2">
            <span><b className="text-tinta">Linha 414:</b> valor está a 24 desvios-padrão da média (Z-Score, MAD, Isolation Forest).</span>
            <span><b className="text-tinta">Linha 415:</b> “Lojaa Centro” aparece em só 0,3% das linhas (Frequência Relativa).</span>
          </figcaption>
        </figure>
      </section>

      <section id="como-usar" className="flex flex-col gap-6 scroll-mt-6">
        <h2 className="text-2xl font-bold tracking-tight">Como usar</h2>
        <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {PASSOS.map(([t, d], i) => (
            <li key={t} className="flex flex-col gap-2 border-t-2 border-tinta pt-3">
              <span className="num text-sm font-bold text-tinta-3">{i + 1}</span>
              <h3 className="font-bold">{t}</h3>
              <p className="text-sm leading-relaxed text-tinta-2">{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-8 border-t border-grade pt-10 md:grid-cols-2">
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-bold">Para colunas numéricas</h2>
          <p className="text-sm leading-relaxed text-tinta-2">
            Z-Score, IQR, Modified Z-Score (MAD), Distância de Mahalanobis, KNN Distance, LOF, Isolation Forest e
            Percentile Fence. Pegam valores extremos numa coluna e combinações improváveis entre colunas.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-bold">Para colunas de texto e categorias</h2>
          <p className="text-sm leading-relaxed text-tinta-2">
            Frequência Relativa, Entropia por Linha, Qui-Quadrado, Teste Binomial, Co-ocorrência de Pares e LOF
            Categórico. Pegam categorias raras, digitadas errado ou combinadas de forma incoerente.
          </p>
        </div>
        <p className="text-sm text-tinta-3 md:col-span-2">
          O arquivo enviado é apagado do servidor após 10 minutos. O histórico das análises guarda só o nome,
          a impressão digital (SHA-256) do arquivo e os resultados.
        </p>
      </section>
    </div>
  );
}
