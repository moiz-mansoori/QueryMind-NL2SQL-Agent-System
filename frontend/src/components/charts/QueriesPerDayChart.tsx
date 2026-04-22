"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { DailyStats } from "@/lib/types";

interface QueriesPerDayChartProps {
  data: DailyStats[];
}

export default function QueriesPerDayChart({ data }: QueriesPerDayChartProps) {
  // Format dates for the X-axis (e.g., "YYYY-MM-DD" -> "MMM DD")
  const formattedData = useMemo(() => {
    return data.map((item) => {
      const date = new Date(item.date);
      const formattedDate = date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      return { ...item, formattedDate };
    }).reverse(); // Reverse to chronological order (API returns descending)
  }, [data]);

  return (
    <div className="w-full h-[300px] bg-[#111118] border border-[#1E1E2E] rounded-2xl p-6">
      <div className="mb-4">
        <h3 className="text-[14px] font-bold text-white tracking-tight">Queries Per Day</h3>
        <p className="text-[12px] text-[#8888A0]">Total queries over the last 7 days</p>
      </div>
      
      <div className="w-full h-[220px] min-w-0">
        <ResponsiveContainer width="99%" height={220}>
          <LineChart data={formattedData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1E1E2E" />
            <XAxis 
              dataKey="formattedDate" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: "#8888A0", fontSize: 11, fontWeight: 500 }}
              dy={10}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: "#8888A0", fontSize: 11, fontWeight: 500 }}
              allowDecimals={false}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: "#0A0A0F", 
                borderColor: "#1E1E2E", 
                borderRadius: "8px",
                boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
                color: "#e8e8f0",
                fontSize: "12px",
                fontWeight: 500
              }}
              itemStyle={{ color: "#00D4FF", fontWeight: 700 }}
              cursor={{ stroke: "#1E1E2E", strokeWidth: 1 }}
            />
            <Line
              type="monotone"
              dataKey="total_count"
              name="Total Queries"
              stroke="#00D4FF"
              strokeWidth={3}
              dot={{ r: 4, fill: "#111118", stroke: "#00D4FF", strokeWidth: 2 }}
              activeDot={{ r: 6, fill: "#00D4FF", stroke: "#0A0A0F", strokeWidth: 2 }}
              animationDuration={1000}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
