"use client";

import { useState } from "react";
import useSWR from "swr";
import { 
  Database, 
  Target, 
  RotateCcw, 
  Clock, 
  Search,
  Eye,
  CheckCircle2,
  XCircle,
  Activity
} from "lucide-react";

import { fetchSummary, fetchDailyStats, fetchHistory, fetchTrace } from "@/lib/api";
import { QueryLogRow, TraceStep } from "@/lib/types";

import MetricCard from "@/components/MetricCard";
import QueriesPerDayChart from "@/components/charts/QueriesPerDayChart";
import SuccessFailureChart from "@/components/charts/SuccessFailureChart";
import SlideOver from "@/components/SlideOver";
import TraceViewer from "@/components/TraceViewer";

// Setup SWR fetchers
const REFRESH_INTERVAL = 30000; // 30 seconds

export default function DashboardPage() {
  const { data: summary, isLoading: isSummaryLoading } = useSWR('/analytics/summary', fetchSummary, { refreshInterval: REFRESH_INTERVAL });
  const { data: dailyStats, isLoading: isDailyLoading } = useSWR('/analytics/daily-stats', fetchDailyStats, { refreshInterval: REFRESH_INTERVAL });
  const { data: history, isLoading: isHistoryLoading } = useSWR('/analytics/history?limit=50', () => fetchHistory(50), { refreshInterval: REFRESH_INTERVAL });

  const [selectedTrace, setSelectedTrace] = useState<{ id: number, steps: TraceStep[] } | null>(null);
  const [isSlideOpen, setIsSlideOpen] = useState(false);
  const [isTraceLoading, setIsTraceLoading] = useState(false);

  const handleRowClick = async (row: QueryLogRow) => {
    // If we already have the trace in the row (e.g. from an old query), use it. 
    // Otherwise, fetch from the dedicated endpoint.
    let steps = row.trace_data;
    
    if (!steps || steps.length === 0) {
      try {
        setIsTraceLoading(true);
        setIsSlideOpen(true); // Open early to show loading state
        const res = await fetchTrace(row.id);
        steps = res.trace_data || [];
      } catch (err) {
        console.error("Failed to fetch trace", err);
        steps = [];
      } finally {
        setIsTraceLoading(false);
      }
    } else {
      setIsSlideOpen(true);
    }
    
    setSelectedTrace({ id: row.id, steps });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in pb-10">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <Activity className="w-8 h-8 text-[#00D4FF]" />
            Observability Dashboard
          </h1>
          <p className="text-[#8888A0] text-[15px]">
            System performance and agent execution metrics. Auto-refreshes every 30s.
          </p>
        </div>
        
        {/* Loading Indicator */}
        {(isSummaryLoading || isDailyLoading || isHistoryLoading) && (
          <div className="flex items-center gap-2 text-[#00D4FF] text-[12px] font-bold uppercase tracking-widest bg-[#00D4FF]/10 px-3 py-1.5 rounded-full border border-[#00D4FF]/20">
            <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            Syncing
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {summary ? (
          <>
            <MetricCard 
              label="Total Queries" 
              value={summary.total_queries} 
              icon={Database} 
              variant="info" 
            />
            <MetricCard 
              label="Success Rate" 
              value={`${summary.success_rate.toFixed(1)}%`} 
              icon={Target} 
              variant={summary.success_rate > 90 ? "success" : "warning"} 
            />
            <MetricCard 
              label="Avg Retries" 
              value={summary.avg_retries.toFixed(2)} 
              icon={RotateCcw} 
              variant={summary.avg_retries > 1 ? "warning" : "info"} 
            />
            <MetricCard 
              label="Avg Latency" 
              value={`${Math.round(summary.avg_latency_ms)}ms`} 
              icon={Clock} 
              variant={summary.avg_latency_ms > 3000 ? "warning" : "info"} 
            />
          </>
        ) : (
           <div className="col-span-4 flex gap-4">
             {[...Array(4)].map((_, i) => <div key={i} className="h-[60px] flex-1 skeleton" />)}
           </div>
        )}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {dailyStats ? (
          <>
            <QueriesPerDayChart data={dailyStats} />
            <SuccessFailureChart data={dailyStats} />
          </>
        ) : (
          <>
            <div className="h-[300px] skeleton rounded-2xl" />
            <div className="h-[300px] skeleton rounded-2xl" />
          </>
        )}
      </div>

      {/* Query History Table */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Search className="w-5 h-5 text-[#8888A0]" />
          Recent Queries
        </h2>
        
        <div className="w-full bg-[#111118] border border-[#1E1E2E] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-[#1A1A25]">
                <tr>
                  <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">Status</th>
                  <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">Question</th>
                  <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">Metrics</th>
                  <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">Time</th>
                  <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E1E2E]">
                {history ? history.map((row) => (
                  <tr key={row.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-5 py-4">
                      {row.success ? (
                        <div className="flex items-center gap-1.5 text-emerald-500">
                          <CheckCircle2 className="w-4 h-4" />
                          <span className="text-[12px] font-bold">Success</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-red-500">
                          <XCircle className="w-4 h-4" />
                          <span className="text-[12px] font-bold">Failed</span>
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <p className="text-[14px] text-white font-medium line-clamp-1">{row.user_question}</p>
                      {row.error_msg && (
                        <p className="text-[12px] text-red-400 mt-1 line-clamp-1">{row.error_msg}</p>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <span className="text-[12px] text-[#8888A0] font-mono flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {Math.round(row.latency_ms)}ms
                        </span>
                        <span className="text-[12px] text-[#8888A0] font-mono flex items-center gap-1">
                          <RotateCcw className="w-3 h-3" /> {row.retries}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-[13px] text-[#555] whitespace-nowrap">
                        {new Date(row.created_at).toLocaleString('en-US', { 
                          month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' 
                        })}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button 
                        onClick={() => handleRowClick(row)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-[12px] font-bold text-white transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5 text-[#00D4FF]" />
                        Inspect
                      </button>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5} className="p-6 text-center text-[#555]">Loading history...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Trace Inspector SlideOver */}
      <SlideOver 
        isOpen={isSlideOpen} 
        onClose={() => setIsSlideOpen(false)}
        title={`Query Trace #${selectedTrace?.id || ""}`}
      >
        {isTraceLoading ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-[#555]">
            <div className="w-6 h-6 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span className="text-[13px] font-bold uppercase tracking-widest">Fetching execution logs...</span>
          </div>
        ) : selectedTrace?.steps ? (
          <TraceViewer steps={selectedTrace.steps} />
        ) : (
          <div className="text-center p-6 text-[#555]">No trace data available for this query.</div>
        )}
      </SlideOver>

    </div>
  );
}
