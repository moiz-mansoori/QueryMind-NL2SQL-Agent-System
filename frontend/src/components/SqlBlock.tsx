"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface SqlBlockProps {
  sql: string;
}

// ── SQL token types ───────────────────────────────────────
type TokenKind =
  | "keyword"
  | "function"
  | "string"
  | "number"
  | "comment"
  | "operator"
  | "punctuation"
  | "identifier"
  | "whitespace";

interface Token {
  kind: TokenKind;
  value: string;
}

const SQL_KEYWORDS = new Set([
  "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
  "FULL", "CROSS", "ON", "AND", "OR", "NOT", "IN", "LIKE", "ILIKE",
  "BETWEEN", "IS", "NULL", "AS", "DISTINCT", "GROUP", "BY", "ORDER",
  "HAVING", "LIMIT", "OFFSET", "INSERT", "INTO", "VALUES", "UPDATE",
  "SET", "DELETE", "CREATE", "TABLE", "INDEX", "DROP", "ALTER", "WITH",
  "UNION", "ALL", "EXCEPT", "INTERSECT", "CASE", "WHEN", "THEN", "ELSE",
  "END", "EXISTS", "ASC", "DESC", "NULLS", "FIRST", "LAST", "OVER",
  "PARTITION", "ROWS", "RANGE", "PRECEDING", "FOLLOWING", "UNBOUNDED",
  "CURRENT", "ROW", "TRUE", "FALSE", "CAST",
]);

const SQL_FUNCTIONS = new Set([
  "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND", "CEIL", "FLOOR",
  "COALESCE", "NULLIF", "DATE", "NOW", "EXTRACT", "DATE_TRUNC",
  "TO_CHAR", "TO_DATE", "CONCAT", "LOWER", "UPPER", "TRIM", "LENGTH",
  "SUBSTRING", "REPLACE", "RANK", "DENSE_RANK", "ROW_NUMBER", "LAG", "LEAD",
]);

function tokenize(sql: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;

  while (i < sql.length) {
    // Single-line comment
    if (sql[i] === "-" && sql[i + 1] === "-") {
      const end = sql.indexOf("\n", i);
      const value = end === -1 ? sql.slice(i) : sql.slice(i, end);
      tokens.push({ kind: "comment", value });
      i += value.length;
      continue;
    }

    // Block comment
    if (sql[i] === "/" && sql[i + 1] === "*") {
      const end = sql.indexOf("*/", i + 2);
      const value = end === -1 ? sql.slice(i) : sql.slice(i, end + 2);
      tokens.push({ kind: "comment", value });
      i += value.length;
      continue;
    }

    // String literal
    if (sql[i] === "'" || sql[i] === '"') {
      const quote = sql[i];
      let j = i + 1;
      while (j < sql.length && !(sql[j] === quote && sql[j - 1] !== "\\")) j++;
      const value = sql.slice(i, j + 1);
      tokens.push({ kind: "string", value });
      i = j + 1;
      continue;
    }

    // Number
    if (/\d/.test(sql[i]) || (sql[i] === "." && /\d/.test(sql[i + 1] ?? ""))) {
      let j = i;
      while (j < sql.length && /[\d.]/.test(sql[j])) j++;
      tokens.push({ kind: "number", value: sql.slice(i, j) });
      i = j;
      continue;
    }

    // Identifier or keyword
    if (/[a-zA-Z_]/.test(sql[i])) {
      let j = i;
      while (j < sql.length && /[\w]/.test(sql[j])) j++;
      const word = sql.slice(i, j);
      const upper = word.toUpperCase();
      let kind: TokenKind = "identifier";
      if (SQL_KEYWORDS.has(upper)) kind = "keyword";
      else if (SQL_FUNCTIONS.has(upper)) kind = "function";
      tokens.push({ kind, value: word });
      i = j;
      continue;
    }

    // Operator
    if (/[=<>!+\-*/%]/.test(sql[i])) {
      tokens.push({ kind: "operator", value: sql[i] });
      i++;
      continue;
    }

    // Punctuation
    if (/[(),;.]/.test(sql[i])) {
      tokens.push({ kind: "punctuation", value: sql[i] });
      i++;
      continue;
    }

    // Whitespace / newlines
    if (/\s/.test(sql[i])) {
      let j = i;
      while (j < sql.length && /\s/.test(sql[j])) j++;
      tokens.push({ kind: "whitespace", value: sql.slice(i, j) });
      i = j;
      continue;
    }

    // Fallback
    tokens.push({ kind: "identifier", value: sql[i] });
    i++;
  }

  return tokens;
}

const TOKEN_COLORS: Record<TokenKind, string> = {
  keyword:     "text-[#C792EA]", // purple
  function:    "text-[#82AAFF]", // blue
  string:      "text-[#C3E88D]", // green
  number:      "text-[#F78C6C]", // orange
  comment:     "text-[#546E7A] italic",
  operator:    "text-[#89DDFF]", // cyan
  punctuation: "text-[#89DDFF]", // cyan
  identifier:  "text-[#EEFFFF]", // near-white
  whitespace:  "",
};

export default function SqlBlock({ sql }: SqlBlockProps) {
  const [copied, setCopied] = useState(false);
  const tokens = tokenize(sql);

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
        <div className="flex items-center gap-2">
          {/* Traffic-light dots */}
          <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#28C840]" />
          <span className="ml-2 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider">
            Generated SQL
          </span>
        </div>
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

      {/* Highlighted Code */}
      <div className="p-4 overflow-x-auto">
        <pre className="font-mono text-[13px] leading-relaxed">
          <code>
            {tokens.map((token, idx) => (
              <span key={idx} className={TOKEN_COLORS[token.kind]}>
                {token.value}
              </span>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}
