"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Activity, Cpu } from "lucide-react";
import { TraceStep } from "@/lib/types";

interface TraceViewerProps {
  steps: TraceStep[];
}

export default function TraceViewer({ steps }: TraceViewerProps) {
  const [expandedIndices, setExpandedIndices] = useState<number[]>([]);

  const toggleStep = (idx: number) => {
    setExpandedIndices((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx]
    );
  };

  if (!steps || steps.length === 0) return null;

  return (
    <div className="w-full space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-4 h-4 text-[#00D4FF]" />
        <h3 className="text-[12px] font-bold text-white uppercase tracking-widest">
          Agent Execution Trace
        </h3>
      </div>

      <div className="space-y-2">
        {steps.map((step, idx) => {
          const isExpanded = expandedIndices.includes(idx);
          const isError = step.status === "error" || step.status === "failure";

          return (
            <div
              key={idx}
              className={`
                bg-[#111118] border rounded-xl overflow-hidden transition-all
                ${isError ? "border-red-500/30" : "border-[#1E1E2E]"}
                ${isExpanded ? "ring-1 ring-[#00D4FF]/20" : ""}
              `}
            >
              {/* Header */}
              <button
                onClick={() => toggleStep(idx)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`
                    p-1.5 rounded-lg
                    ${isError ? "bg-red-500/10 text-red-400" : "bg-[#00D4FF]/10 text-[#00D4FF]"}
                  `}
                  >
                    <Cpu className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex flex-col items-start ml-2">
                    <span className="text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">
                      Node
                    </span>
                    <span className="text-[14px] font-bold text-white">
                      {step.node.replaceAll("_", " ")}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <span
                    className={`
                    px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-tighter
                    ${
                      isError
                        ? "bg-red-500/20 text-red-500"
                        : "bg-emerald-500/20 text-emerald-500"
                    }
                  `}
                  >
                    {step.status}
                  </span>
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-[#555]" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-[#555]" />
                  )}
                </div>
              </button>

              {/* Expandable Content */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-[#1E1E2E] bg-[#0A0A0F]">
                  <div className="grid grid-cols-1 gap-4 pt-4">
                    {Object.entries(step).map(([key, value]) => {
                      if (key === "node" || key === "status") return null;
                      return (
                        <div key={key} className="space-y-1">
                          <span className="text-[10px] font-bold text-[#555] uppercase tracking-widest block">
                            {key}
                          </span>
                          <div className="bg-[#111118] border border-[#1E1E2E] rounded-lg p-3 overflow-x-auto">
                            <pre className="font-mono text-[12px] text-[#8888A0]">
                              <code>
                                {typeof value === "string"
                                  ? value
                                  : JSON.stringify(value, null, 2)}
                              </code>
                            </pre>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
