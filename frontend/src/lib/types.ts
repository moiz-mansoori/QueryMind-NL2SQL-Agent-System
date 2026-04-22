export interface QueryMetrics {
  retries: number;
  latency_ms: number;
  success: boolean;
}

export interface TraceStep {
  node: string;
  status: string;
  [key: string]: any; // Allow arbitrary keys for individual node traces
}

export interface QueryResponse {
  answer: string;
  sql: string;
  rows: Record<string, any>[];
  metrics: QueryMetrics;
  error: string | null;
  trace_steps: TraceStep[];
}

export interface AnalyticsSummary {
  total_queries: number;
  success_rate: number;
  avg_retries: number;
  avg_latency_ms: number;
}

export interface QueryLogRow {
  id: number;
  user_question: string;
  generated_sql: string | null;
  final_sql: string | null;
  result_rows: number;
  error_msg: string | null;
  retries: number;
  latency_ms: number;
  success: boolean;
  trace_data: any | null;
  created_at: string;
}

export interface DailyStats {
  date: string;
  total_count: number;
  success_count: number;
  failure_count: number;
}
