import { type RouteConfig, index, layout, route } from "@react-router/dev/routes";

// Todas as rotas compartilham o layout (barra de navegação + container principal).
export default [
  layout("routes/layout.tsx", [
    index("routes/homepage.tsx"),
    route("upload", "routes/upload_archives.tsx"),
    route("decisions", "routes/filtercolumns.tsx"),
    route("decisions/models", "routes/modelspage.tsx"),
    route("report", "routes/reportpage.tsx"),
  ]),
] satisfies RouteConfig;
