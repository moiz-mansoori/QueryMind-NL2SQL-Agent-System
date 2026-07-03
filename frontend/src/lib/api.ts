/**
 * QueryMind API Client
 *
 * Centralized fetch-based API client.
 * All backend calls go through this module.
 */

import type {
  QueryResponse,
  AnalyticsSummary,
  QueryLogRow,
  DailyStats,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Query ───────────────────────────────────────────────

export async function postQuery(
  question: string,
  includeTrace: boolean = false
): Promise<QueryResponse> {
  const res = await fetch(
    `${API_URL}/query?include_trace=${includeTrace}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(
      err?.detail ?? `Query failed with status ${res.status}`
    );
  }

  return res.json();
}

// ── Analytics ───────────────────────────────────────────

export async function fetchSummary(): Promise<AnalyticsSummary> {
  const res = await fetch(`${API_URL}/analytics/summary`);
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

export async function fetchHistory(
  limit: number = 50
): Promise<QueryLogRow[]> {
  const res = await fetch(`${API_URL}/analytics/history?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function fetchFailures(
  limit: number = 50
): Promise<QueryLogRow[]> {
  const res = await fetch(`${API_URL}/analytics/failures?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch failures");
  return res.json();
}

export async function fetchDailyStats(): Promise<DailyStats[]> {
  const res = await fetch(`${API_URL}/analytics/daily-stats`);
  if (!res.ok) throw new Error("Failed to fetch daily stats");
  return res.json();
}

export async function fetchTrace(
  queryId: number
): Promise<{ trace_data: any[] }> {
  const res = await fetch(`${API_URL}/analytics/trace/${queryId}`);
  if (!res.ok) throw new Error("Failed to fetch trace");
  return res.json();
}

export function streamQuery(
  question: string,
  onEvent: (event: any) => void,
  onError: (err: any) => void
): () => void {
  const url = `${API_URL}/query/stream?question=${encodeURIComponent(question)}`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent(data);
      if (data.event === "complete" || data.event === "error") {
        eventSource.close();
      }
    } catch (err) {
      onError(err);
      eventSource.close();
    }
  };

  eventSource.onerror = (err) => {
    onError(new Error("EventSource connection failed"));
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}

