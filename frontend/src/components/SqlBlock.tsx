"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface SqlBlockProps {
  sql: string;
}

export default function SqlBlock({ sql }: SqlBlockProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy!", err);
    }
  };

  return (
    <div className="group relative w-full bg-[#0A0A0F] rounded-xl border border-[#1E1E2E] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#1E1E2E] bg-white/5">
        <span className="text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">
          Generated SQL
        </span>
        <button
          onClick={copyToClipboard}
          className="p-1.5 rounded-md hover:bg-white/10 text-[#8888A0] hover:text-white transition-colors"
          title="Copy to clipboard"
        >
          {copied ? (
            <Check className="w-4 h-4 text-[#00C853]" />
          ) : (
            <Copy className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Code */}
      <div className="p-4 overflow-x-auto">
        <pre className="font-mono text-[13px] leading-relaxed text-[#00D4FF]">
          <code>{sql}</code>
        </pre>
      </div>
    </div>
  );
}
