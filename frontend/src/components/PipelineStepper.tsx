"use client";

import { CheckCircle2, AlertCircle, Loader2, Play } from "lucide-react";
import { TraceStep } from "@/lib/types";

interface PipelineStepperProps {
  activeNode: string | null;
  steps: TraceStep[];
  isCompleted: boolean;
  error: string | null;
}

interface StepConfig {
  id: string;
  label: string;
  description: string;
}

const ALL_STEPS: StepConfig[] = [
  { id: "query_classifier", label: "Query Classifier", description: "Analyzing intent of the user prompt" },
  { id: "schema_retriever", label: "Schema Retriever", description: "Finding relevant tables and columns" },
  { id: "sql_generator", label: "SQL Generator", description: "Writing the PostgreSQL query" },
  { id: "sql_validator", label: "SQL Validator", description: "Parsing and validating SQL syntax & safety" },
  { id: "sql_executor", label: "SQL Executor", description: "Executing SQL on PostgreSQL" },
  { id: "sql_corrector", label: "SQL Corrector", description: "Self-correcting errors (only runs if needed)" },
  { id: "result_formatter", label: "Result Formatter", description: "Generating natural language answer" },
  { id: "query_logger", label: "Query Logger", description: "Saving metrics & steps to logs" }
];

export default function PipelineStepper({ activeNode, steps, isCompleted, error }: PipelineStepperProps) {
  // Determine the status of each step configuration
  const getStepStatus = (stepId: string) => {
    // Check if the step exists in completed trace steps
    const trace = steps.find(s => s.node === stepId);
    
    if (trace) {
      if (trace.status === "error" || trace.status === "failure") {
        return "error";
      }
      return "completed";
    }

    if (activeNode === stepId) {
      return "active";
    }

    // Special case for corrector: only show active/completed if it actually ran
    if (stepId === "sql_corrector") {
      const ranCorrector = steps.some(s => s.node === "sql_corrector");
      if (!ranCorrector && activeNode !== "sql_corrector") {
        return "skipped";
      }
    }

    // If completed and we haven't hit this step, it was skipped (e.g. general greeting routes bypass SQL execution)
    if (isCompleted) {
      return "skipped";
    }

    return "pending";
  };

  const getStepDetails = (stepId: string) => {
    const trace = steps.find(s => s.node === stepId);
    if (!trace) return null;

    if (stepId === "query_classifier") {
      return `Intent: ${trace.intent || "unknown"}`;
    }
    if (stepId === "schema_retriever") {
      return `Retrieved ${trace.retrieved_tables_count || 0} tables`;
    }
    if (stepId === "sql_generator" && trace.generated_sql) {
      return "SQL query drafted";
    }
    if (stepId === "sql_validator") {
      return trace.status === "success" ? "Validation passed" : trace.error || "Validation failed";
    }
    if (stepId === "sql_executor") {
      return trace.status === "success" ? `Fetched ${trace.row_count || 0} rows` : "Execution failed";
    }
    if (stepId === "sql_corrector") {
      return `Attempt ${trace.attempt || 1} completed`;
    }
    if (stepId === "result_formatter") {
      return "Answer formulated";
    }
    if (stepId === "query_logger" && trace.latency_ms) {
      return `Logged (Latency: ${trace.latency_ms}ms)`;
    }
    return null;
  };

  // Filter steps so we don't clutter with sql_corrector if it was skipped
  const visibleSteps = ALL_STEPS.filter(step => {
    if (step.id === "sql_corrector") {
      const status = getStepStatus("sql_corrector");
      return status !== "skipped";
    }
    return true;
  });

  const getStepDuration = (stepId: string) => {
    const trace = steps.find(s => s.node === stepId);
    return trace && trace.duration_ms ? `${Math.round(trace.duration_ms)}ms` : null;
  };

  // Find active step index and calculate progress
  const activeStepIndex = visibleSteps.findIndex(s => s.id === activeNode);
  const currentStepNum = isCompleted ? visibleSteps.length : Math.max(1, activeStepIndex + 1);
  const progressPercent = Math.round((currentStepNum / visibleSteps.length) * 100);

  return (
    <div className="w-full bg-[#111118] border border-[#1E1E2E] rounded-2xl p-6 shadow-xl animate-in space-y-6">
      <div className="flex items-center justify-between border-b border-[#1E1E2E] pb-4">
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Agent Execution Pipeline
          </h3>
          <p className="text-xs text-[#8888A0]">
            Step {currentStepNum} of {visibleSteps.length} · {progressPercent}% complete
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isCompleted && !error && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#00D4FF]/10 border border-[#00D4FF]/20 text-[#00D4FF] text-[10px] font-bold uppercase tracking-wider">
              <Loader2 className="w-3 h-3 animate-spin" />
              Agent Thinking
            </span>
          )}
          {isCompleted && !error && (
            <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-[10px] font-bold uppercase tracking-wider">
              Success
            </span>
          )}
          {error && (
            <span className="px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-500 text-[10px] font-bold uppercase tracking-wider">
              Failed
            </span>
          )}
        </div>
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-[#1E1E2E]">
        {visibleSteps.map((step, idx) => {
          const status = getStepStatus(step.id);
          const duration = getStepDuration(step.id);
          
          let iconColor = "text-[#3a3a4a] bg-[#111118] border-[#1E1E2E]";
          let textColor = "text-[#8888A0]";
          let detailColor = "text-[#555]";
          let icon = <Play className="w-3.5 h-3.5" />;

          if (status === "active") {
            iconColor = "text-[#00D4FF] bg-[#00D4FF]/10 border-[#00D4FF]/30 ring-4 ring-[#00D4FF]/5";
            textColor = "text-white font-semibold";
            detailColor = "text-[#00D4FF]";
            icon = <Loader2 className="w-3.5 h-3.5 animate-spin" />;
          } else if (status === "completed") {
            iconColor = "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
            textColor = "text-white";
            detailColor = "text-emerald-400";
            icon = <CheckCircle2 className="w-3.5 h-3.5" />;
          } else if (status === "error") {
            iconColor = "text-red-500 bg-red-500/10 border-red-500/20";
            textColor = "text-white";
            detailColor = "text-red-400";
            icon = <AlertCircle className="w-3.5 h-3.5" />;
          }

          const details = getStepDetails(step.id);

          return (
            <div key={step.id} className="relative flex gap-4 transition-all duration-300">
              {/* Timeline dot */}
              <div className={`absolute -left-[21px] top-0 w-[12px] h-[12px] rounded-full border-2 transition-all duration-300 ${
                status === "completed" ? "bg-emerald-500 border-emerald-500 scale-110 shadow-[0_0_8px_rgba(16,185,129,0.3)]" :
                status === "active" ? "bg-[#00D4FF] border-[#00D4FF] scale-125 shadow-[0_0_8px_rgba(0,212,255,0.3)] animate-pulse" :
                status === "error" ? "bg-red-500 border-red-500 scale-110 shadow-[0_0_8px_rgba(239,68,68,0.3)]" :
                "bg-[#111118] border-[#1E1E2E]"
              }`} />

              <div className="flex-1 flex flex-col md:flex-row md:items-center justify-between gap-1">
                <div>
                  <h4 className={`text-xs md:text-sm font-medium flex items-center gap-2 ${textColor}`}>
                    {step.label}
                    {duration && (
                      <span className="text-[10px] font-mono text-[#555]">
                        ({duration})
                      </span>
                    )}
                  </h4>
                  <p className="text-[11px] text-[#555] leading-relaxed">
                    {step.description}
                  </p>
                </div>
                {details && (
                  <div className={`text-[10px] md:text-xs font-mono px-2 py-0.5 rounded border self-start md:self-center transition-all ${
                    status === "completed" ? "bg-emerald-500/5 border-emerald-500/10 text-emerald-400" :
                    status === "active" ? "bg-[#00D4FF]/5 border-[#00D4FF]/10 text-[#00D4FF]" :
                    status === "error" ? "bg-red-500/5 border-red-500/10 text-red-400" :
                    "bg-white/5 border-[#1E1E2E]"
                  }`}>
                    {details}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

