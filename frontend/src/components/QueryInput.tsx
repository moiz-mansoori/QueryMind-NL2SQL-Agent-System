"use client";

import { useState } from "react";
import { Search } from "lucide-react";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export default function QueryInput({ onSubmit, isLoading }: QueryInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative flex items-center w-full shadow-sm rounded-xl bg-[#111118] border border-[#1E1E2E] focus-within:border-[#00D4FF]/50 focus-within:ring-1 focus-within:ring-[#00D4FF]/50 transition-all duration-200">
        <div className="pl-4 pr-2 flex items-center justify-center text-[#8888A0]">
          <Search className="w-5 h-5" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your database... (e.g., How many customers do we have?)"
          className="flex-1 bg-transparent border-none outline-none py-4 pr-4 text-white placeholder:text-[#555] text-[15px]"
          disabled={isLoading}
        />
        <div className="pr-2">
          <button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="flex items-center justify-center bg-[#00D4FF] hover:bg-[#00B4DF] text-[#0A0A0F] font-semibold px-5 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-[#0A0A0F]/20 border-t-[#0A0A0F] rounded-full animate-spin" />
                <span>Running</span>
              </div>
            ) : (
              "Ask AI"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
