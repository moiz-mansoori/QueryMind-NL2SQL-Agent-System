import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  variant?: "info" | "success" | "error" | "warning";
}

export default function MetricCard({
  label,
  value,
  icon: Icon,
  variant = "info",
}: MetricCardProps) {
  const colorMap = {
    info: "text-[#00D4FF] bg-[#00D4FF]/10 border-[#00D4FF]/20",
    success: "text-[#00C853] bg-[#00C853]/10 border-[#00C853]/20",
    error: "text-[#FF3D57] bg-[#FF3D57]/10 border-[#FF3D57]/20",
    warning: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  };


  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-[#111118] border border-[#1E1E2E] rounded-full shadow-sm">
      <div className={`p-1.5 rounded-full ${colorMap[variant]}`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-[14px] font-bold text-white tracking-tight">
          {value}
        </span>
        <span className="text-[10px] font-bold text-[#8888A0] uppercase tracking-widest">
          {label}
        </span>
      </div>
    </div>
  );
}
