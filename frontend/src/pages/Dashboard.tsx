import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface HealthResponse {
  status: string;
}

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthResponse>("/health"),
  });

  return (
    <div className="p-8">
      <h1 className="text-3xl font-semibold mb-6">FP&A Copilot</h1>
      <div className="rounded-lg border border-border bg-card p-6 max-w-sm">
        <h2 className="text-sm font-medium text-muted-foreground mb-2">
          API Status
        </h2>
        {isLoading && (
          <p className="text-muted-foreground">Checking...</p>
        )}
        {isError && (
          <p className="text-destructive font-medium">API unreachable</p>
        )}
        {data && (
          <p className="text-lg font-semibold text-green-600">
            {data.status === "healthy" ? "API Healthy" : data.status}
          </p>
        )}
      </div>
    </div>
  );
}
