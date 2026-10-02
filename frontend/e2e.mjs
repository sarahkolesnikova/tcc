// Teste de ponta a ponta do fluxo: início → upload → colunas → modelos → relatório → exportações.
// Uso: node e2e.mjs <arquivo.csv> [pasta-de-capturas]   (frontend em :5173 e backend no ar)
import { chromium } from "playwright";

const [arquivo, pasta = "."] = process.argv.slice(2);
const URL = process.env.E2E_URL ?? "http://localhost:5173";
const falhas = [];
const ok = (cond, msg) => { if (!cond) falhas.push(msg); console.log(`${cond ? "ok  " : "FALHA"} ${msg}`); };

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
page.on("pageerror", (e) => falhas.push(`erro JS: ${e.message}`));
await page.route(/fonts\.(googleapis|gstatic)/, (r) => r.abort());

await page.goto(URL);
await page.getByRole("heading", { level: 1, name: /registros fora do padrão/ }).waitFor();
ok(true, "homepage carrega");
await page.screenshot({ path: `${pasta}/1_homepage.png`, fullPage: true });
await page.getByRole("link", { name: "Analisar uma planilha" }).click();
await page.waitForURL("**/upload");

await page.setInputFiles("#arquivo", arquivo);
ok(await page.getByTestId("arquivo-escolhido").isVisible(), "arquivo escolhido aparece");
await page.screenshot({ path: `${pasta}/2_upload.png`, fullPage: true });
await page.getByRole("button", { name: "Enviar e continuar" }).click();
await page.waitForURL("**/decisions");
await page.getByRole("button", { name: "Continuar para os modelos" }).waitFor();
await page.screenshot({ path: `${pasta}/3_colunas.png`, fullPage: true });
await page.getByRole("button", { name: "Continuar para os modelos" }).click();

await page.waitForURL("**/decisions/models");
await page.getByRole("button", { name: "Gerar relatório" }).waitFor();
await page.waitForSelector("text=Distância de Mahalanobis");
const marcados = await page.locator("input[type=checkbox]:checked").count();
ok(marcados === 14, `14 modelos marcados por padrão (achou ${marcados})`);
await page.locator("#contaminacao").fill("0.02");
await page.screenshot({ path: `${pasta}/4_modelos.png`, fullPage: true });
await page.getByRole("button", { name: "Gerar relatório" }).click();

await page.waitForURL("**/report", { waitUntil: "commit" });
await page.getByTestId("tabela-consenso").waitFor({ timeout: 60000 });
const primeira = page.getByTestId("tabela-consenso").locator("tbody tr").first();
ok((await primeira.locator("td").first().innerText()).trim() === "8", "linha 8 (valor 25.000) é a primeira do consenso");
await primeira.click();
ok(await page.getByText(/desvios-padrão/).first().isVisible(), "motivos aparecem ao clicar na linha");
ok(await page.locator(".recharts-surface").count() >= 3, "três gráficos renderizados");
await page.waitForTimeout(800);
await page.screenshot({ path: `${pasta}/5_relatorio.png`, fullPage: true });

for (const [nome, ext] of [["Baixar CSV com marcações", ".csv"], ["Baixar PDF", ".pdf"]]) {
  const [dl] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: nome }).click()]);
  ok(dl.suggestedFilename().endsWith(ext), `${nome} baixa ${dl.suggestedFilename()}`);
}
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({ path: `${pasta}/6_relatorio_celular.png`, fullPage: false });
const largura = await page.evaluate(() => document.documentElement.scrollWidth);
ok(largura <= 390, `sem rolagem horizontal no celular (largura ${largura})`);

await browser.close();
if (falhas.length) { console.error(`\n${falhas.length} falha(s)`); process.exit(1); }
console.log("\ne2e aprovado");
