"use client";

import { useState } from "react";
import { 
  Zap, 
  RotateCcw, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  Code2,
  Table as TableIcon,
  Eye,
  EyeOff
} from "lucide-react";

import QueryInput from "@/components/QueryInput";
import ResultTable from "@/components/ResultTable";
import SqlBlock from "@/components/SqlBlock";
import MetricCard from "@/components/MetricCard";
import TraceViewer from "@/components/TraceViewer";

import { postQuery } from "@/lib/api";
import { QueryResponse } from "@/lib/types";

export default function QueryPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");
  const [showTrace, setShowTrace] = useState(false);
  const [isTraceLoading, setIsTraceLoading] = useState(false);

  const handleQuery = async (question: string, includeTrace: boolean = false) => {
    setIsLoading(true);
    setError(null);
    setLastQuestion(question);

    try {
      const data = await postQuery(question, includeTrace);
      setResponse(data);
      if (includeTrace) {
        setShowTrace(true);
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
      setResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTrace = async () => {
    if (!response || !lastQuestion) return;

    if (!showTrace && response.trace_steps.length === 0) {
      // Re-fetch with trace if we don't have it
      setIsTraceLoading(true);
      try {
        const data = await postQuery(lastQuestion, true);
        setResponse(data);
        setShowTrace(true);
      } catch (err: any) {
        setError("Failed to fetch execution trace");
      } finally {
        setIsTraceLoading(false);
      }
    } else {
      setShowTrace(!showTrace);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-10">
      {/* Hero Section */}
      <div className="space-y-2">
        <h1 className="text-4xl font-extrabold tracking-tighter text-white">
          Database <span className="text-[#00D4FF]">Copilot</span>
        </h1>
        <p className="text-[#8888A0] text-lg max-w-2xl">
          Ask complex questions in natural language. Our AI writes, validates, 
          and executes the SQL for you with autonomous self-correction.
        </p>
      </div>

      {/* Input Area */}
      <section className="bg-[#111118] p-1 rounded-2xl border border-[#1E1E2E] shadow-2xl">
        <QueryInput onSubmit={(q) => handleQuery(q, false)} isLoading={isLoading} />
      </section>

      {/* Results Section */}
      {(response || error || isLoading) && (
        <div className="space-y-8 animate-in">
          
          {/* Error State */}
          {error && (
            <div className="flex items-start gap-4 p-5 bg-red-500/10 border border-red-500/20 rounded-2xl">
              <AlertCircle className="w-6 h-6 text-[#FF3D57] shrink-0" />
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-white tracking-tight">Execution Failed</h3>
                <p className="text-red-400/80 leading-relaxed text-[15px]">{error}</p>
              </div>
            </div>
          )}

          {/* Success State */}
          {response && !error && (
            <>
              {/* Answer Card */}
              <div className="flex flex-col gap-6 p-8 bg-[#111118] border border-[#1E1E2E] rounded-3xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-8 opacity-[0.03] group-hover:opacity-[0.05] transition-opacity pointer-events-none">
                  <Zap className="w-64 h-64 text-[#00D4FF]" />
                </div>

                <div className="flex items-center gap-2">
                  <div className="px-3 py-1 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center gap-1.5 border border-emerald-500/20">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span className="text-[11px] font-bold uppercase tracking-wider">Analysis Complete</span>
                  </div>
                </div>

                <p className="text-[20px] font-medium text-white leading-relaxed max-w-3xl">
                  {response.answer}
                </p>

                {/* Metrics Badges */}
                <div className="flex flex-wrap gap-3 mt-4">
                  <MetricCard 
                    label="Latency" 
                    value={`${response.metrics.latency_ms}ms`} 
                    icon={Clock} 
                  />
                  <MetricCard 
                    label="Retries" 
                    value={response.metrics.retries} 
                    icon={RotateCcw} 
                    variant={response.metrics.retries > 0 ? "warning" : "info"}
                  />
                </div>
              </div>

              {/* SQL & Trace Tabs Control */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2 text-[#8888A0]">
                    <Code2 className="w-4 h-4" />
                    <span className="text-[12px] font-bold uppercase tracking-widest">Execution Details</span>
                  </div>
                </div>
                <button 
                  onClick={toggleTrace}
                  disabled={isTraceLoading}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-[12px] font-bold text-white transition-all disabled:opacity-50"
                >
                  {isTraceLoading ? (
                    <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  ) : showTrace ? (
                    <><EyeOff className="w-4 h-4" /> Hide Trace</>
                  ) : (
                    <><Eye className="w-4 h-4" /> Show Trace Replay</>
                  )}
                </button>
              </div>

              {/* SQL Block */}
              <SqlBlock sql={response.sql} />

              {/* Trace Viewer (Optional) */}
              {showTrace && response.trace_steps && (
                <TraceViewer steps={response.trace_steps} />
              )}

              {/* Data Table */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-[#8888A0]">
                  <TableIcon className="w-4 h-4" />
                  <span className="text-[12px] font-bold uppercase tracking-widest">Result Dataset</span>
                </div>
                <ResultTable rows={response.rows} />
              </div>
            </>
          )}

          {/* Loading Skeleton during re-fetches or initial load */}
          {isLoading && !response && (
            <div className="space-y-6">
              <div className="h-40 w-full skeleton" />
              <div className="h-20 w-full skeleton" />
              <div className="h-64 w-full skeleton" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
