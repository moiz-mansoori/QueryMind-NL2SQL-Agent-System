"use client";

import { useState } from "react";
import useSWR from "swr";
import { 
  AlertTriangle, 
  Search,
  Eye,
  Clock,
  RotateCcw
} from "lucide-react";

import { fetchFailures, fetchTrace } from "@/lib/api";
import { QueryLogRow, TraceStep } from "@/lib/types";

import SlideOver from "@/components/SlideOver";
import TraceViewer from "@/components/TraceViewer";

const REFRESH_INTERVAL = 30000;

export default function FailuresPage() {
  const { data: failures, isLoading } = useSWR('/analytics/failures?limit=50', () => fetchFailures(50), { refreshInterval: REFRESH_INTERVAL });

  const [selectedTrace, setSelectedTrace] = useState<{ id: number, steps: TraceStep[] } | null>(null);
  const [isSlideOpen, setIsSlideOpen] = useState(false);
  const [isTraceLoading, setIsTraceLoading] = useState(false);

  const handleRowClick = async (row: QueryLogRow) => {
    let steps = row.trace_data;
    
    if (!steps || steps.length === 0) {
      try {
        setIsTraceLoading(true);
        setIsSlideOpen(true);
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
            <AlertTriangle className="w-8 h-8 text-[#FF3D57]" />
            Failed Queries
          </h1>
          <p className="text-[#8888A0] text-[15px]">
            Review queries that could not be successfully executed or self-corrected by the agent.
          </p>
        </div>
        
        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-center gap-2 text-[#00D4FF] text-[12px] font-bold uppercase tracking-widest bg-[#00D4FF]/10 px-3 py-1.5 rounded-full border border-[#00D4FF]/20">
            <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            Syncing
          </div>
        )}
      </div>

      {/* Failures Table */}
      <div className="w-full bg-[#111118] border border-[#1E1E2E] rounded-xl overflow-hidden">
        <div className="overflow-x-auto min-h-[400px]">
          <table className="w-full text-left border-collapse">
            <thead className="bg-[#1A1A25]">
              <tr>
                <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider w-[40%]">Question & Error</th>
                <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">Metrics</th>
                <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">Time</th>
                <th className="px-5 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E1E2E]">
              {isLoading && !failures ? (
                // Skeleton Rows
                [...Array(5)].map((_, i) => (
                  <tr key={i}>
                    <td className="px-5 py-4"><div className="h-10 skeleton rounded w-3/4" /></td>
                    <td className="px-5 py-4"><div className="h-6 skeleton rounded w-1/2" /></td>
                    <td className="px-5 py-4"><div className="h-6 skeleton rounded w-1/2" /></td>
                    <td className="px-5 py-4"><div className="h-8 skeleton rounded w-20 float-right" /></td>
                  </tr>
                ))
              ) : failures && failures.length === 0 ? (
                // Empty State
                <tr>
                  <td colSpan={4}>
                    <div className="flex flex-col items-center justify-center py-20 text-[#555]">
                      <Search className="w-12 h-12 mb-4 opacity-50" />
                      <p className="text-[15px] font-medium text-white/50">No failures found</p>
                      <p className="text-[13px] mt-1">The agent is successfully processing all queries.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                // Data Rows
                failures?.map((row) => (
                  <tr key={row.id} className="hover:bg-red-500/[0.02] transition-colors group">
                    <td className="px-5 py-4 max-w-sm">
                      <p className="text-[14px] text-white font-medium mb-1 line-clamp-2" title={row.user_question}>
                        {row.user_question}
                      </p>
                      <div className="bg-red-500/10 border border-red-500/20 rounded-md p-2 mt-2">
                        <p className="text-[12px] text-red-400 font-mono line-clamp-3" title={row.error_msg || "Unknown error"}>
                          {row.error_msg || "Unknown error"}
                        </p>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-col gap-2">
                        <span className="text-[12px] text-[#8888A0] font-mono flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-[#00D4FF]" /> 
                          {Math.round(row.latency_ms)}ms
                        </span>
                        <span className="text-[12px] text-[#8888A0] font-mono flex items-center gap-1.5">
                          <RotateCcw className="w-3.5 h-3.5 text-[#00D4FF]" /> 
                          {row.retries} retries
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
                    <td className="px-5 py-4 text-right align-top">
                      <button 
                        onClick={() => handleRowClick(row)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-[12px] font-bold text-white transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5 text-[#00D4FF]" />
                        Inspect Trace
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trace Inspector SlideOver */}
      <SlideOver 
        isOpen={isSlideOpen} 
        onClose={() => setIsSlideOpen(false)}
        title={`Failed Query Trace #${selectedTrace?.id || ""}`}
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
