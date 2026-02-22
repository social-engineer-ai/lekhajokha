"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { ClientHeader } from "@/components/client-workspace/ClientHeader";
import { TabNav } from "@/components/client-workspace/TabNav";

interface Client {
  id: string;
  business_name: string;
  gstin: string | null;
  city: string | null;
  ingest_email: string | null;
}

export default function ClientWorkspaceLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const clientId = params.clientId as string;
  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Client>(`/clients/${clientId}`)
      .then(setClient)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [clientId]);

  if (loading) {
    return <div className="text-muted-foreground">Loading client...</div>;
  }

  if (!client) {
    return <div className="text-destructive">Client not found</div>;
  }

  return (
    <div className="space-y-4">
      <ClientHeader
        businessName={client.business_name}
        gstin={client.gstin}
        city={client.city}
        ingestEmail={client.ingest_email}
      />
      <TabNav clientId={clientId} />
      <div className="pt-2">{children}</div>
    </div>
  );
}
