"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";
import { DailyStats } from "@/lib/types";

interface SuccessFailureChartProps {
  data: DailyStats[];
}

export default function SuccessFailureChart({ data }: SuccessFailureChartProps) {
  const formattedData = useMemo(() => {
    return data.map((item) => {
      const date = new Date(item.date);
      const formattedDate = date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      return { ...item, formattedDate };
    }).reverse();
  }, [data]);

  return (
    <div className="w-full h-[300px] bg-[#111118] border border-[#1E1E2E] rounded-2xl p-6">
      <div className="mb-4">
        <h3 className="text-[14px] font-bold text-white tracking-tight">Success vs Failure</h3>
        <p className="text-[12px] text-[#8888A0]">Query outcomes over the last 7 days</p>
      </div>
      
      <div className="w-full h-[220px] min-w-0">
        <ResponsiveContainer width="99%" height={220}>
          <BarChart data={formattedData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
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
              cursor={{ fill: "#1E1E2E", opacity: 0.4 }}
            />
            <Legend 
              wrapperStyle={{ fontSize: "11px", fontWeight: 600, paddingTop: "10px" }}
              iconType="circle"
              iconSize={8}
            />
            <Bar 
              dataKey="success_count" 
              name="Success" 
              fill="#00C853" 
              stackId="a"
              animationDuration={1000}
            />
            <Bar 
              dataKey="failure_count" 
              name="Failure" 
              fill="#FF3D57" 
              radius={[4, 4, 0, 0]} 
              stackId="a"
              animationDuration={1000}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
