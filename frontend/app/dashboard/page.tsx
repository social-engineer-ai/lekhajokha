"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { ClientListTable } from "@/components/dashboard/ClientListTable";

interface Client {
  id: string;
  business_name: string;
  gstin: string | null;
  city: string | null;
  contact_name: string | null;
  gst_filing_frequency: string;
  is_active: boolean;
}

export default function DashboardPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Client[]>("/clients/")
      .then(setClients)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-muted-foreground">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <StatsCards totalClients={clients.length} />
      <ClientListTable clients={clients} />
    </div>
  );
}
