import { Links, Meta, Outlet, Scripts, ScrollRestoration, isRouteErrorResponse } from "react-router";
import type { Route } from "./+types/root";
import "./app.css";

export const links: Route.LinksFunction = () => [
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&display=swap" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Anomaly Detector</title>
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return <Outlet />;
}

export function HydrateFallback() {
  return <p className="p-8 text-tinta-2">Carregando…</p>;
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  const msg = isRouteErrorResponse(error) ? `${error.status} — ${error.statusText}` : (error as Error)?.message;
  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold">Algo deu errado</h1>
      <p className="mt-2 text-tinta-2">{msg}</p>
      <a className="mt-4 inline-block font-semibold text-acao underline" href="/">Voltar ao início</a>
    </main>
  );
}
