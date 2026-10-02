import { Link, Outlet } from "react-router";

export default function Layout() {
  return (
    <div className="min-h-screen">
      <nav className="border-b border-grade bg-folha">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight">
            <svg viewBox="0 0 24 24" className="size-6" aria-hidden="true">
              <rect x="2" y="3" width="20" height="18" rx="2" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <path d="M2 9h20M2 15h20M9 3v18M16 3v18" stroke="currentColor" strokeWidth="1" opacity=".45" />
              <rect x="9.6" y="9.6" width="5.8" height="4.8" fill="var(--color-marca)" />
            </svg>
            Anomaly Detector
          </Link>
          <Link to="/upload" className="rounded-md px-3 py-2 text-sm font-semibold text-acao hover:bg-papel">
            Nova análise
          </Link>
        </div>
      </nav>
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
