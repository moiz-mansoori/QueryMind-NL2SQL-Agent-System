"use client";

interface ResultTableProps {
  rows: Record<string, any>[];
}

export default function ResultTable({ rows }: ResultTableProps) {
  if (!rows || rows.length === 0) {
    return (
      <div className="w-full py-12 flex flex-col items-center justify-center bg-[#111118] border border-[#1E1E2E] rounded-xl text-[#555]">
        <p>No rows returned</p>
      </div>
    );
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className="w-full bg-[#111118] border border-[#1E1E2E] rounded-xl overflow-hidden">
      <div className="overflow-x-auto max-h-[400px]">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 bg-[#1A1A25] shadow-sm z-10">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-3 text-[11px] font-bold text-[#8888A0] uppercase tracking-wider border-b border-[#1E1E2E]"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E1E2E]">
            {rows.map((row, idx) => (
              <tr
                key={idx}
                className="hover:bg-white/[0.02] transition-colors group"
              >
                {columns.map((col) => {
                  const val = row[col];
                  return (
                    <td
                      key={`${idx}-${col}`}
                      className="px-4 py-3 text-[14px] text-white/80 font-medium"
                    >
                      {val === null ? (
                        <span className="text-[#555] italic">null</span>
                      ) : typeof val === "object" ? (
                        JSON.stringify(val)
                      ) : (
                        String(val)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2 border-t border-[#1E1E2E] bg-white/5 flex items-center justify-between">
        <span className="text-[11px] text-[#555]">
          Showing {rows.length} {rows.length === 1 ? "row" : "rows"}
        </span>
      </div>
    </div>
  );
}
