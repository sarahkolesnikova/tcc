import type { Config } from "@react-router/dev/config";

// SPA: o estado da sessão vive no LocalStorage do navegador; não há renderização no servidor.
export default { ssr: false } satisfies Config;
