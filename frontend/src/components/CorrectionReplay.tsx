"use client";

import { useState } from "react";
import { Sparkles, AlertCircle, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import { TraceStep } from "@/lib/types";
import SqlBlock from "./SqlBlock";

interface CorrectionReplayProps {
  steps: TraceStep[];
}

export default function CorrectionReplay({ steps }: CorrectionReplayProps) {
  const [isOpen, setIsOpen] = useState(true);

  // Extract correction attempts from trace_steps
  const corrections = steps.filter(s => s.node === "sql_corrector");

  if (corrections.length === 0) return null;

  return (
    <div className="w-full bg-[#111118]/80 border border-orange-500/20 rounded-2xl overflow-hidden shadow-2xl animate-in">
      {/* Header Accordion Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-6 py-4 bg-orange-500/5 hover:bg-orange-500/10 border-b border-[#1E1E2E] transition-all"
      >
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-orange-500/10 text-orange-400">
            <Sparkles className="w-4 h-4 animate-pulse" />
          </div>
          <div className="text-left">
            <h3 className="text-xs md:text-sm font-bold text-white uppercase tracking-wider">
              Autonomous Self-Correction Replay
            </h3>
            <p className="text-[10px] md:text-xs text-[#8888A0]">
              The agent recovered from {corrections.length} execution/validation {corrections.length === 1 ? "error" : "errors"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 text-[9px] font-bold uppercase tracking-wider">
            {corrections.length} {corrections.length === 1 ? "retry" : "retries"}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-[#555]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#555]" />
          )}
        </div>
      </button>

      {/* Accordion Content */}
      {isOpen && (
        <div className="p-6 space-y-8 bg-[#0A0A0F]/50">
          {corrections.map((corr, idx) => (
            <div key={idx} className="space-y-4">
              <div className="flex items-center justify-between text-xs text-[#8888A0] font-mono border-b border-[#1E1E2E] pb-2">
                <span>Attempt #{corr.attempt || idx + 1}</span>
                <span className="text-orange-400">Fixed</span>
              </div>

              {/* Grid Diff */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Left Side: Failed SQL */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-red-400 font-mono">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Failed Query Template</span>
                  </div>
                  <div className="rounded-xl border border-red-500/20 bg-red-500/[0.02]">
                    <SqlBlock sql={corr.original_sql || ""} />
                  </div>
                </div>

                {/* Right Side: Corrected SQL */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Corrected SQL Query</span>
                  </div>
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.02]">
                    <SqlBlock sql={corr.corrected_sql || ""} />
                  </div>
                </div>

              </div>

              {/* Error Detail Message Box */}
              {corr.error_fixed && (
                <div className="mt-2 p-4 rounded-xl bg-red-500/5 border border-red-500/10 text-[11px] md:text-xs font-mono text-red-300 leading-relaxed overflow-x-auto">
                  <div className="text-[10px] uppercase font-bold text-red-400 tracking-wider mb-1">
                    Error Log Caught By Validator/Executor:
                  </div>
                  <code>{corr.error_fixed}</code>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
