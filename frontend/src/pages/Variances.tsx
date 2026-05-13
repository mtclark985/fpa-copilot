import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { VarianceRecord } from "@/types/api";

const severityBadge: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

export default function Variances() {
  const [selectedPeriod, setSelectedPeriod] = useState("2026-06");
  const [selectedVariance, setSelectedVariance] = useState<VarianceRecord | null>(null);

  const { data: variances, isLoading } = useQuery({
    queryKey: ["variances", selectedPeriod],
    queryFn: () =>
      apiFetch<VarianceRecord[]>(`/variances?period=${selectedPeriod}`),
  });

  const periods = [
    "2026-01",
    "2026-02",
    "2026-03",
    "2026-04",
    "2026-05",
    "2026-06",
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Variances</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Forecast vs. actual variance analysis
        </p>
      </div>

      {/* Period selector */}
      <div className="flex gap-2">
        {periods.map((p) => (
          <button
            key={p}
            onClick={() => {
              setSelectedPeriod(p);
              setSelectedVariance(null);
            }}
            className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
              selectedPeriod === p
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border bg-card hover:bg-muted"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="flex gap-6">
        {/* Variance list */}
        <div className="flex-1 min-w-0">
          {isLoading ? (
            <div className="text-muted-foreground text-center py-12">
              Loading variances...
            </div>
          ) : (
            <div className="rounded-lg border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                      Cost Center
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                      Category
                    </th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">
                      Variance $
                    </th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">
                      Variance %
                    </th>
                    <th className="text-center px-4 py-3 font-medium text-muted-foreground">
                      Severity
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                      Rationale
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {variances?.map((v, i) => (
                    <tr
                      key={v.id}
                      onClick={() => setSelectedVariance(v)}
                      className={`cursor-pointer transition-colors ${
                        selectedVariance?.id === v.id
                          ? "bg-primary/5"
                          : i % 2 === 0
                            ? "bg-card hover:bg-muted/30"
                            : "bg-muted/20 hover:bg-muted/40"
                      }`}
                    >
                      <td className="px-4 py-2 font-medium">
                        {v.cost_center_name}
                      </td>
                      <td className="px-4 py-2 capitalize">{v.category}</td>
                      <td
                        className={`px-4 py-2 text-right tabular-nums ${
                          v.variance_amount > 0
                            ? "text-red-600"
                            : "text-green-600"
                        }`}
                      >
                        {formatCurrency(v.variance_amount)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {formatPercent(v.variance_pct)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {v.agent_severity ? (
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${severityBadge[v.agent_severity]}`}
                          >
                            {v.agent_severity}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            --
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-muted-foreground truncate max-w-[200px]">
                        {v.agent_rationale || "--"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {variances?.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No variances for this period.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Drill-down panel */}
        {selectedVariance && (
          <div className="w-80 flex-shrink-0 rounded-lg border border-border bg-card p-5 space-y-4 self-start sticky top-20">
            <h3 className="font-semibold text-lg">Variance Detail</h3>

            <div className="space-y-3 text-sm">
              <div>
                <p className="text-muted-foreground text-xs uppercase tracking-wider">
                  Cost Center
                </p>
                <p className="font-medium">
                  {selectedVariance.cost_center_name}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-muted-foreground text-xs uppercase tracking-wider">
                    Forecast
                  </p>
                  <p className="font-medium tabular-nums">
                    {formatCurrency(selectedVariance.forecast_amount)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs uppercase tracking-wider">
                    Actual
                  </p>
                  <p className="font-medium tabular-nums">
                    {formatCurrency(selectedVariance.actual_amount)}
                  </p>
                </div>
              </div>

              <div className="border-t border-border pt-3">
                <p className="text-muted-foreground text-xs uppercase tracking-wider">
                  Variance Decomposition
                </p>
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Volume (Headcount)
                    </p>
                    <p className="font-medium tabular-nums">
                      {formatCurrency(selectedVariance.volume_variance)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Rate (Cost/Head)
                    </p>
                    <p className="font-medium tabular-nums">
                      {formatCurrency(selectedVariance.rate_variance)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="border-t border-border pt-3">
                <p className="text-muted-foreground text-xs uppercase tracking-wider">
                  Materiality Score
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        selectedVariance.materiality_score >= 60
                          ? "bg-red-500"
                          : selectedVariance.materiality_score >= 30
                            ? "bg-yellow-500"
                            : "bg-green-500"
                      }`}
                      style={{
                        width: `${selectedVariance.materiality_score}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs font-medium tabular-nums">
                    {selectedVariance.materiality_score.toFixed(0)}
                  </span>
                </div>
              </div>

              {selectedVariance.agent_rationale && (
                <div className="border-t border-border pt-3">
                  <p className="text-muted-foreground text-xs uppercase tracking-wider">
                    Agent Assessment
                  </p>
                  <div className="mt-2 space-y-2">
                    <div className="flex gap-2">
                      {selectedVariance.agent_severity && (
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${severityBadge[selectedVariance.agent_severity]}`}
                        >
                          {selectedVariance.agent_severity}
                        </span>
                      )}
                      {selectedVariance.agent_unexpectedness && (
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          {selectedVariance.agent_unexpectedness.replace(
                            /_/g,
                            " "
                          )}
                        </span>
                      )}
                    </div>
                    <p className="text-sm">{selectedVariance.agent_rationale}</p>
                    {selectedVariance.agent_suggested_action && (
                      <p className="text-xs text-muted-foreground">
                        Suggested:{" "}
                        <span className="font-medium capitalize">
                          {selectedVariance.agent_suggested_action}
                        </span>
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
