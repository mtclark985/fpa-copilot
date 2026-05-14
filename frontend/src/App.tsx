import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Forecast from "@/pages/Forecast";
import Variances from "@/pages/Variances";
import Close from "@/pages/Close";
import Proposals from "@/pages/Proposals";
import DataAndAssumptions from "@/pages/DataAndAssumptions";
import WhatIf from "@/pages/WhatIf";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/variances" element={<Variances />} />
            <Route path="/close" element={<Close />} />
            <Route path="/proposals" element={<Proposals />} />
            <Route path="/data-and-assumptions" element={<DataAndAssumptions />} />
            <Route path="/what-if" element={<WhatIf />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
