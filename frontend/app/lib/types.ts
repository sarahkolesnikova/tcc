export type TipoColuna = "numeric" | "categorical";

export interface Coluna { name: string; type: TipoColuna; missing: number; unique: number }

export interface Arquivo {
  file_id: string; filename: string; size_bytes: number; rows: number;
  sha256: string; created_at: string; columns: Coluna[];
}

export interface ModeloInfo { id: string; name: string; type: TipoColuna; description: string }
export interface Modelos { numeric: ModeloInfo[]; categorical: ModeloInfo[] }

export interface Parametros {
  models: string[]; numeric_columns: string[]; categorical_columns: string[]; threshold: number;
}

export interface ResultadoModelo {
  id: string; name: string; type: TipoColuna; anomalies: number; rate: number;
  threshold: number | null; elapsed_ms: number;
  rows: { row: number; score: number; reason: string | null }[];
}

export interface LinhaConsenso {
  row: number; votes: number; consensus_score: number;
  values: Record<string, string | number | null>;
  reasons: { model: string; reason: string }[];
}

export interface Relatorio {
  file: { id: string; filename: string; sha256: string; size_bytes: number; rows: number };
  parameters: Parametros;
  summary: { rows: number; flagged_rows: number; flagged_by_majority: number; models_run: number };
  models: ResultadoModelo[];
  consensus: LinhaConsenso[];
  votes_histogram: { votes: number; rows: number }[];
  statistics: {
    numeric: { column: string; count: number; missing: number; mean: number; std: number; min: number;
               q1: number; median: number; q3: number; max: number }[];
    categorical: { column: string; count: number; unique: number; top: string; top_freq: number; missing: number }[];
  };
  scatter: null | { x: string; y: string; points: { row: number; x: number; y: number; votes: number }[] };
}
