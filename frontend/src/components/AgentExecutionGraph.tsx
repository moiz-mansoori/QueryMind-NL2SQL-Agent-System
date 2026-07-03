"use client";

import { useState } from "react";
import { GitBranch, Clock, RefreshCw, Activity, CheckCircle2, AlertTriangle } from "lucide-react";
import { TraceStep } from "@/lib/types";
import SqlBlock from "./SqlBlock";

interface AgentExecutionGraphProps {
  steps: TraceStep[];
  isStreaming?: boolean;
  activeNode?: string | null;
}

interface NodePosition {
  id: string;
  label: string;
  x: number;
  y: number;
  description: string;
}

// Fixed SVG layout coordinates for our nodes
const NODES: NodePosition[] = [
  { id: "query_classifier", label: "Query Classifier", x: 250, y: 40, description: "Classifies query intent" },
  { id: "direct_responder", label: "Direct Responder", x: 70, y: 130, description: "Bypasses DB for simple queries" },
  { id: "schema_retriever", label: "Schema Retriever", x: 430, y: 130, description: "Fetches relevant tables" },
  { id: "sql_generator", label: "SQL Generator", x: 430, y: 230, description: "Drafts the raw SQL" },
  { id: "sql_validator", label: "SQL Validator", x: 430, y: 330, description: "Checks query safety & syntax" },
  { id: "sql_corrector", label: "SQL Corrector", x: 250, y: 380, description: "Fixes errors with LLM feedback" },
  { id: "sql_executor", label: "SQL Executor", x: 430, y: 430, description: "Runs query on Postgres" },
  { id: "result_formatter", label: "Result Formatter", x: 430, y: 530, description: "Forms natural language answer" },
  { id: "failure_handler", label: "Failure Handler", x: 250, y: 485, description: "Manages fallback solutions" },
  { id: "query_logger", label: "Query Logger", x: 250, y: 610, description: "Stores query execution stats" },
];

interface Edge {
  from: string;
  to: string;
  // Controls control points for curved paths: e.g. "M x y Q x y x y" or simple line "M x y L x y"
  path: string;
}

const EDGES: Edge[] = [
  // Classifier split
  { from: "query_classifier", to: "direct_responder", path: "M 200 60 L 120 110" },
  { from: "query_classifier", to: "schema_retriever", path: "M 300 60 L 380 110" },
  // Direct responder convergence
  { from: "direct_responder", to: "query_logger", path: "M 70 160 L 70 560 Q 70 610 200 610" },
  // Main path
  { from: "schema_retriever", to: "sql_generator", path: "M 430 160 L 430 200" },
  { from: "sql_generator", to: "sql_validator", path: "M 430 260 L 430 300" },
  // Validator branch to Corrector or Executor
  { from: "sql_validator", to: "sql_corrector", path: "M 380 340 L 300 370" },
  { from: "sql_validator", to: "sql_executor", path: "M 430 360 L 430 400" },
  // Corrector cycle back to Validator
  { from: "sql_corrector", to: "sql_validator", path: "M 300 390 Q 350 420 380 360" },
  // Corrector to Failure Handler
  { from: "sql_corrector", to: "failure_handler", path: "M 250 410 L 250 455" },
  // Executor branch
  { from: "sql_executor", to: "result_formatter", path: "M 430 460 L 430 500" },
  { from: "sql_executor", to: "sql_corrector", path: "M 380 440 L 300 390" },
  // Success / Failure convergence to Logger
  { from: "result_formatter", to: "query_logger", path: "M 430 560 L 430 580 Q 430 610 300 610" },
  { from: "failure_handler", to: "query_logger", path: "M 250 515 L 250 580" },
];

export default function AgentExecutionGraph({ steps = [], isStreaming = false, activeNode = null }: AgentExecutionGraphProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("query_classifier");

  // Lookup node status based on trace step completion or current streaming state
  const getNodeStatus = (nodeId: string) => {
    const matched = steps.find(s => s.node === nodeId);
    if (matched) {
      if (matched.status === "error" || matched.status === "failure") return "error";
      return "success";
    }
    if (activeNode === nodeId) {
      return "active";
    }
    
    // Check if corrector node was skipped or visited
    if (nodeId === "sql_corrector") {
      const ranCorrector = steps.some(s => s.node === "sql_corrector");
      if (!ranCorrector && activeNode !== "sql_corrector") return "skipped";
    }
    if (nodeId === "failure_handler") {
      const ranFailure = steps.some(s => s.node === "failure_handler");
      if (!ranFailure && activeNode !== "failure_handler") return "skipped";
    }

    if (steps.length > 0 && !isStreaming) {
      return "skipped";
    }
    return "inactive";
  };

  // Evaluate if an edge was traveled
  const isEdgeTraveled = (edge: Edge) => {
    const fromStatus = getNodeStatus(edge.from);
    const toStatus = getNodeStatus(edge.to);
    
    // An edge is active/traveled if its source node completed or target node is active/completed
    if (fromStatus === "success" && (toStatus === "success" || toStatus === "active" || toStatus === "error")) {
      // Logic split from classifier
      if (edge.from === "query_classifier") {
        const classifierStep = steps.find(s => s.node === "query_classifier");
        const intent = classifierStep?.intent || "database_query";
        if (intent === "database_query" && edge.to === "direct_responder") return false;
        if (intent !== "database_query" && edge.to === "schema_retriever") return false;
      }
      // Logic split from validator
      if (edge.from === "sql_validator") {
        const validatorStep = steps.find(s => s.node === "sql_validator");
        const hasError = validatorStep?.status === "error" || validatorStep?.status === "failure" || validatorStep?.error_message;
        if (hasError && edge.to === "sql_executor") return false;
        if (!hasError && edge.to === "sql_corrector") return false;
      }
      // Logic split from executor
      if (edge.from === "sql_executor") {
        const executorStep = steps.find(s => s.node === "sql_executor");
        const isSuccess = executorStep?.status === "success";
        if (isSuccess && edge.to === "sql_corrector") return false;
        if (!isSuccess && edge.to === "result_formatter") return false;
      }
      return true;
    }
    return false;
  };

  const getStatusColorClass = (status: string) => {
    switch (status) {
      case "active": return "fill-[#00D4FF]/10 stroke-[#00D4FF] shadow-[0_0_15px_rgba(0,212,255,0.4)]";
      case "success": return "fill-emerald-500/10 stroke-emerald-500";
      case "error": return "fill-red-500/10 stroke-red-500";
      case "skipped": return "fill-white/[0.02] stroke-[#2A2A3A] opacity-30";
      default: return "fill-white/[0.02] stroke-[#1E1E2E]";
    }
  };

  const selectedStepDetails = steps.find(s => s.node === selectedNodeId);
  const selectedNodeMeta = NODES.find(n => n.id === selectedNodeId);
  const selectedNodeStatus = selectedNodeId ? getNodeStatus(selectedNodeId) : null;

  // Pipeline execution stats
  const totalExecutionTime = steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0);
  const retries = steps.filter(s => s.node === "sql_corrector").length;
  const visitedNodesCount = steps.length;
  let pipelineStatus = "Idle";
  if (isStreaming) pipelineStatus = "Running";
  else if (steps.length > 0) {
    const hasError = steps.some(s => s.status === "error" || s.node === "failure_handler");
    pipelineStatus = hasError ? "Failed" : retries > 0 ? "Recovered Successfully" : "Success";
  }

  return (
    <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-6 bg-[#111118] border border-[#1E1E2E] rounded-3xl p-6 shadow-2xl animate-in">
      
      {/* Visual Execution graph pane */}
      <div className="lg:col-span-2 flex flex-col items-center justify-center bg-[#0A0A0F] border border-[#1E1E2E] rounded-2xl p-4 overflow-hidden relative min-h-[500px]">
        <div className="absolute top-4 left-4 flex items-center gap-2 text-[11px] text-[#8888A0] font-bold uppercase tracking-wider">
          <GitBranch className="w-3.5 h-3.5 text-[#00D4FF]" />
          <span>Interactive Execution Graph</span>
        </div>

        <svg width="100%" height="670" viewBox="0 0 540 670" className="max-w-[500px]">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#1E1E2E" />
            </marker>
            <marker id="arrow-active" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#00D4FF" />
            </marker>
            <marker id="arrow-success" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10B981" />
            </marker>
          </defs>

          {/* Connectors (Edges) */}
          {EDGES.map((edge, idx) => {
            const active = isEdgeTraveled(edge);
            const toStatus = getNodeStatus(edge.to);
            let marker = "url(#arrow)";
            let stroke = "#1E1E2E";
            let dashArray = "";
            let animationClass = "";

            if (active) {
              if (toStatus === "success") {
                stroke = "#10B981";
                marker = "url(#arrow-success)";
              } else {
                stroke = "#00D4FF";
                marker = "url(#arrow-active)";
                dashArray = "4, 4";
                animationClass = "[stroke-dashoffset:20] animate-[dash_1s_linear_infinite]";
              }
            }

            return (
              <path
                key={idx}
                d={edge.path}
                fill="none"
                stroke={stroke}
                strokeWidth={active ? 2.5 : 1.5}
                markerEnd={marker}
                strokeDasharray={dashArray}
                className={animationClass}
              />
            );
          })}

          {/* Nodes */}
          {NODES.map((node) => {
            const status = getNodeStatus(node.id);
            const isSelected = selectedNodeId === node.id;
            const borderColors = getStatusColorClass(status);

            return (
              <g
                key={node.id}
                transform={`translate(${node.x - 70}, ${node.y - 20})`}
                onClick={() => setSelectedNodeId(node.id)}
                className="cursor-pointer group"
              >
                {/* Node Box */}
                <rect
                  width="140"
                  height="40"
                  rx="10"
                  className={`transition-all duration-300 ${borderColors} ${
                    isSelected 
                      ? "stroke-[2.5px] fill-white/[0.05]" 
                      : "stroke-[1.5px] hover:stroke-white/30 hover:fill-white/[0.02]"
                  }`}
                />
                
                {/* Node Label Text */}
                <text
                  x="70"
                  y="24"
                  textAnchor="middle"
                  className={`text-[11px] font-bold select-none tracking-tight transition-colors ${
                    status === "active" ? "fill-[#00D4FF]" :
                    status === "success" ? "fill-emerald-400" :
                    status === "error" ? "fill-red-400" :
                    status === "skipped" ? "fill-[#444]" : "fill-[#8888A0] group-hover:fill-white"
                  }`}
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Node Details & Pipeline Telemetry side panel */}
      <div className="flex flex-col justify-between space-y-6">
        
        {/* Selected Node Details Box */}
        <div className="bg-[#0A0A0F] border border-[#1E1E2E] rounded-2xl p-5 flex-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[#1E1E2E] pb-3 mb-4">
              <span className="text-[10px] font-bold uppercase tracking-widest text-[#8888A0]">Node Attributes</span>
              {selectedNodeStatus && (
                <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide ${
                  selectedNodeStatus === "success" ? "bg-emerald-500/10 text-emerald-400" :
                  selectedNodeStatus === "active" ? "bg-[#00D4FF]/10 text-[#00D4FF] animate-pulse" :
                  selectedNodeStatus === "error" ? "bg-red-500/10 text-red-400" :
                  "bg-white/5 text-[#555]"
                }`}>
                  {selectedNodeStatus}
                </span>
              )}
            </div>

            {selectedNodeMeta && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-bold text-white leading-tight">{selectedNodeMeta.label}</h4>
                  <p className="text-[11px] text-[#555] mt-0.5">{selectedNodeMeta.description}</p>
                </div>

                {selectedStepDetails ? (
                  <div className="space-y-3 text-xs">
                    {selectedStepDetails.duration_ms !== undefined && (
                      <div className="flex items-center justify-between font-mono bg-white/[0.02] border border-[#1E1E2E] p-2 rounded-lg">
                        <span className="text-[#555]">Duration</span>
                        <span className="text-white">{Math.round(selectedStepDetails.duration_ms)}ms</span>
                      </div>
                    )}

                    {selectedStepDetails.intent && (
                      <div className="flex items-center justify-between font-mono bg-white/[0.02] border border-[#1E1E2E] p-2 rounded-lg">
                        <span className="text-[#555]">Parsed Intent</span>
                        <span className="text-white">{selectedStepDetails.intent}</span>
                      </div>
                    )}

                    {selectedStepDetails.retrieved_tables_count !== undefined && (
                      <div className="flex items-center justify-between font-mono bg-white/[0.02] border border-[#1E1E2E] p-2 rounded-lg">
                        <span className="text-[#555]">Retrieved Tables</span>
                        <span className="text-white">{selectedStepDetails.retrieved_tables_count}</span>
                      </div>
                    )}

                    {selectedStepDetails.row_count !== undefined && (
                      <div className="flex items-center justify-between font-mono bg-white/[0.02] border border-[#1E1E2E] p-2 rounded-lg">
                        <span className="text-[#555]">Result Rows</span>
                        <span className="text-white">{selectedStepDetails.row_count}</span>
                      </div>
                    )}

                    {selectedStepDetails.attempt !== undefined && (
                      <div className="flex items-center justify-between font-mono bg-white/[0.02] border border-[#1E1E2E] p-2 rounded-lg">
                        <span className="text-[#555]">Correction Retry</span>
                        <span className="text-orange-400">Attempt #{selectedStepDetails.attempt}</span>
                      </div>
                    )}

                    {/* Code Snippet parameters formatting */}
                    {(selectedStepDetails.generated_sql || selectedStepDetails.corrected_sql || selectedStepDetails.original_sql) && (
                      <div className="space-y-1.5 pt-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#555]">Generated SQL:</span>
                        <div className="max-h-[140px] overflow-y-auto border border-[#1E1E2E] rounded-lg">
                          <SqlBlock sql={selectedStepDetails.generated_sql || selectedStepDetails.corrected_sql || selectedStepDetails.original_sql || ""} />
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-32 flex items-center justify-center border border-dashed border-[#1E1E2E] rounded-xl text-center p-4">
                    <span className="text-[11px] text-[#555]">
                      {selectedNodeStatus === "skipped" 
                        ? "This node was bypassed during routing logic execution."
                        : "Waiting for query execution trace to reach this node..."}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
          
          <p className="text-[10px] text-[#555] font-mono mt-4 text-center">
            Click any graph node to inspect execution details
          </p>
        </div>

        {/* Pipeline Summary Telemetry Cards */}
        <div className="bg-[#0A0A0F] border border-[#1E1E2E] rounded-2xl p-5 space-y-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#8888A0] block border-b border-[#1E1E2E] pb-2">
            Execution Telemetry
          </span>
          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 bg-white/[0.02] border border-[#1E1E2E] rounded-xl space-y-1">
              <span className="text-[9px] text-[#555] uppercase tracking-wider block">Visited Nodes</span>
              <div className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-[#00D4FF]" />
                <span className="text-white font-bold">{visitedNodesCount} / 10</span>
              </div>
            </div>

            <div className="p-3 bg-white/[0.02] border border-[#1E1E2E] rounded-xl space-y-1">
              <span className="text-[9px] text-[#555] uppercase tracking-wider block">Duration</span>
              <div className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#00D4FF]" />
                <span className="text-white font-bold">{Math.round(totalExecutionTime)}ms</span>
              </div>
            </div>

            <div className="p-3 bg-white/[0.02] border border-[#1E1E2E] rounded-xl space-y-1">
              <span className="text-[9px] text-[#555] uppercase tracking-wider block">Retries</span>
              <div className="flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5 text-orange-400" />
                <span className="text-white font-bold">{retries}</span>
              </div>
            </div>

            <div className="p-3 bg-white/[0.02] border border-[#1E1E2E] rounded-xl space-y-1">
              <span className="text-[9px] text-[#555] uppercase tracking-wider block">Status</span>
              <div className="flex items-center gap-1.5">
                {pipelineStatus === "Success" || pipelineStatus === "Recovered Successfully" ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : pipelineStatus === "Running" ? (
                  <Loader2 className="w-3.5 h-3.5 text-[#00D4FF] animate-spin" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                )}
                <span className="text-white font-bold truncate">{pipelineStatus}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
      
      {/* Dynamic inline styles for animating active path vectors */}
      <style jsx global>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -20;
          }
        }
      `}</style>
    </div>
  );
}

// Simple fallback loader helper
function Loader2({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );
}
