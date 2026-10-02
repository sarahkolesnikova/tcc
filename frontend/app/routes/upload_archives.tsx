import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Aviso, Botao, Pagina } from "~/components/ui";
import { enviarArquivo } from "~/lib/api";
import { bytes } from "~/lib/formato";
import { limparSessao, salvarSessao } from "~/lib/session";

const LIMITE = 50 * 1024 * 1024;
const ACEITOS = [".csv", ".xlsx", ".xls"];

export function meta() {
  return [{ title: "Enviar planilha · Anomaly Detector" }];
}

export function validarArquivo(f: File): string | null {
  const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
  if (!ACEITOS.includes(ext)) return `“${f.name}” não é CSV, XLSX ou XLS.`;
  if (f.size > LIMITE) return `O arquivo tem ${bytes(f.size)}; o limite é 50 MB.`;
  if (f.size === 0) return "O arquivo está vazio.";
  return null;
}

export default function UploadArchives() {
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [arrastando, setArrastando] = useState(false);

  function escolher(f: File | undefined) {
    if (!f) return;
    const problema = validarArquivo(f);
    setErro(problema);
    setArquivo(problema ? null : f);
  }

  async function enviar() {
    if (!arquivo) return;
    setEnviando(true);
    setErro(null);
    try {
      const resp = await enviarArquivo(arquivo);
      limparSessao();
      salvarSessao({ arquivo: resp });
      navigate("/decisions");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Pagina etapa={0} titulo="Envie a planilha"
      descricao="CSV, XLSX ou XLS de até 50 MB. A primeira linha deve ter os nomes das colunas.">
      <div
        onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
        onDragLeave={() => setArrastando(false)}
        onDrop={(e) => { e.preventDefault(); setArrastando(false); escolher(e.dataTransfer.files[0]); }}
        className={`flex max-w-3xl flex-col items-start gap-4 rounded-lg border-2 border-dashed p-8 transition-colors ${
          arrastando ? "border-acao bg-folha" : "border-grade-forte bg-folha/60"}`}
      >
        <input ref={input} id="arquivo" type="file" accept={ACEITOS.join(",")} className="sr-only"
          onChange={(e) => escolher(e.target.files?.[0])} />
        <p className="text-tinta-2">Arraste o arquivo para cá ou</p>
        <Botao variante="secundario" type="button" onClick={() => input.current?.click()}>Escolher arquivo</Botao>
        {arquivo && (
          <p className="text-sm" data-testid="arquivo-escolhido">
            <b>{arquivo.name}</b> <span className="num text-tinta-3">· {bytes(arquivo.size)}</span>
          </p>
        )}
      </div>
      {erro && <div className="max-w-3xl"><Aviso>{erro}</Aviso></div>}
      <div>
        <Botao onClick={enviar} disabled={!arquivo || enviando}>
          {enviando ? "Enviando…" : "Enviar e continuar"}
        </Botao>
      </div>
    </Pagina>
  );
}
