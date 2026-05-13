import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { AdvanceMonthResponse } from "@/types/api";

export default function Close() {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<AdvanceMonthResponse | null>(null);

  const advanceMutation = useMutation({
    mutationFn: () =>
      apiFetch<AdvanceMonthResponse>("/close/advance-month", {
        method: "POST",
      }),
    onSuccess: (data) => {
      setResult(data);
      // Invalidate all queries so dashboard/forecast/variances refresh
      queryClient.invalidateQueries();
    },
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-semibold">Monthly Close</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Advance the simulation by one month. This generates payroll actuals,
          calculates variances, and runs the variance detection agent.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 space-y-4">
        <button
          onClick={() => advanceMutation.mutate()}
          disabled={advanceMutation.isPending}
          className="px-6 py-3 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {advanceMutation.isPending
            ? "Processing..."
            : "Advance to Next Month"}
        </button>

        {advanceMutation.isPending && (
          <div className="text-sm text-muted-foreground">
            Generating actuals, calculating variances, running agent
            analysis...
          </div>
        )}

        {advanceMutation.isError && (
          <div className="text-sm text-destructive">
            Error: {(advanceMutation.error as Error).message}
          </div>
        )}

        {result && (
          <div className="rounded-md border border-border bg-muted/30 p-4 space-y-3">
            <h3 className="font-semibold">
              Month Closed: {result.period}
            </h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-muted-foreground">Story: </span>
                <span className="font-medium">{result.story}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Events: </span>
                <span>{result.events}</span>
              </div>
              <div className="grid grid-cols-3 gap-4 pt-2">
                <div>
                  <p className="text-xs text-muted-foreground uppercase">
                    Actuals
                  </p>
                  <p className="font-semibold">
                    {result.actuals_created.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">
                    Variances
                  </p>
                  <p className="font-semibold">
                    {result.variances_calculated}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">
                    Agent Assessments
                  </p>
                  <p className="font-semibold">
                    {result.agent_assessments}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
