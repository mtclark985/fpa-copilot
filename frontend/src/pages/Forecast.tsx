import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { ForecastLine, CostCenter } from "@/types/api";

export default function Forecast() {
  const [selectedCC, setSelectedCC] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");

  const { data: costCenters } = useQuery({
    queryKey: ["cost-centers"],
    queryFn: () => apiFetch<CostCenter[]>("/cost-centers"),
  });

  const { data: forecastData, isLoading } = useQuery({
    queryKey: ["forecast", selectedCC],
    queryFn: () => {
      const params = new URLSearchParams();
      if (selectedCC) params.set("cost_center_id", selectedCC);
      const qs = params.toString();
      return apiFetch<ForecastLine[]>(`/forecast${qs ? `?${qs}` : ""}`);
    },
  });

  // Group by period and category for table display
  const tableData = useMemo(() => {
    if (!forecastData) return [];

    const filtered = selectedCategory
      ? forecastData.filter((l) => l.category === selectedCategory)
      : forecastData;

    // Group by cost_center_name + period
    const grouped = new Map<string, Map<string, { amount: number; headcount: number }>>();

    for (const line of filtered) {
      const key = line.cost_center_name;
      if (!grouped.has(key)) grouped.set(key, new Map());
      const periods = grouped.get(key)!;

      const existing = periods.get(line.period) || { amount: 0, headcount: 0 };
      existing.amount += line.amount;
      existing.headcount = line.headcount_eop;
      periods.set(line.period, existing);
    }

    return Array.from(grouped.entries()).map(([ccName, periods]) => ({
      costCenter: ccName,
      periods: Object.fromEntries(periods),
    }));
  }, [forecastData, selectedCategory]);

  const allPeriods = useMemo(() => {
    if (!forecastData) return [];
    const set = new Set(forecastData.map((l) => l.period));
    return Array.from(set).sort();
  }, [forecastData]);

  const categories = ["salary", "bonus", "benefits", "taxes"];

  const handleExport = () => {
    if (!forecastData) return;
    const header = ["Cost Center", "Period", "Category", "Amount", "Headcount"];
    const rows = forecastData.map((l) => [
      l.cost_center_name,
      l.period,
      l.category,
      l.amount.toFixed(2),
      l.headcount_eop.toString(),
    ]);
    const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "forecast.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Forecast</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Active forecast: Initial Plan FY26
          </p>
        </div>
        <button
          onClick={handleExport}
          className="px-4 py-2 text-sm font-medium rounded-md border border-border bg-card hover:bg-muted transition-colors"
        >
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={selectedCC}
          onChange={(e) => setSelectedCC(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-card"
        >
          <option value="">All Cost Centers</option>
          {costCenters?.map((cc) => (
            <option key={cc.id} value={cc.id}>
              {cc.code} - {cc.name}
            </option>
          ))}
        </select>
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-card"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-muted-foreground text-center py-12">
          Loading forecast data...
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground sticky left-0 bg-muted/50">
                  Cost Center
                </th>
                {allPeriods.map((p) => (
                  <th
                    key={p}
                    className="text-right px-4 py-3 font-medium text-muted-foreground whitespace-nowrap"
                  >
                    {p}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData.map((row, i) => (
                <tr
                  key={row.costCenter}
                  className={i % 2 === 0 ? "bg-card" : "bg-muted/20"}
                >
                  <td className="px-4 py-2 font-medium sticky left-0 bg-inherit">
                    {row.costCenter}
                  </td>
                  {allPeriods.map((p) => (
                    <td key={p} className="text-right px-4 py-2 tabular-nums">
                      {row.periods[p]
                        ? formatCurrency(row.periods[p].amount)
                        : "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {tableData.length === 0 && (
            <p className="text-center text-muted-foreground py-8">
              No forecast data available.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
