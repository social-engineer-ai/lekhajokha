"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { formatDateLong } from "@/lib/format";
import { BankAccountAddModal } from "@/components/bank/BankAccountAddModal";

interface Client {
  id: string;
  business_name: string;
  gstin: string | null;
  pan: string | null;
  state_code: string | null;
  city: string | null;
  address: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  ingest_email: string | null;
  gst_username: string | null;
  gst_filing_frequency: string;
  created_at: string;
  bank_accounts: {
    id: string;
    bank_name: string;
    account_number: string;
    ifsc_code: string | null;
    is_primary: boolean;
  }[];
}

export default function ClientOverviewPage() {
  const params = useParams();
  const clientId = params.clientId as string;
  const [client, setClient] = useState<Client | null>(null);
  const [showAddBank, setShowAddBank] = useState(false);

  const fetchClient = () => {
    apiFetch<Client>(`/clients/${clientId}`).then(setClient).catch(() => {});
  };

  useEffect(() => {
    fetchClient();
  }, [clientId]);

  if (!client) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Business Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <Row label="GSTIN" value={client.gstin} />
          <Row label="PAN" value={client.pan} />
          <Row label="City" value={client.city} />
          <Row label="Address" value={client.address} />
          <Row label="GST Filing" value={client.gst_filing_frequency} />
          <Row label="GST Username" value={client.gst_username} />
          <Row label="Added" value={formatDateLong(client.created_at)} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Contact & Ingest</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <Row label="Contact" value={client.contact_name} />
          <Row label="Phone" value={client.contact_phone} />
          <Row label="Email" value={client.contact_email} />
          <Row label="Ingest Email" value={client.ingest_email} mono />
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Bank Accounts</CardTitle>
          <Button variant="outline" size="sm" onClick={() => setShowAddBank(true)}>
            + Add Account
          </Button>
        </CardHeader>
        <CardContent>
          {client.bank_accounts.length === 0 ? (
            <p className="text-muted-foreground text-sm">No bank accounts added yet.</p>
          ) : (
            <div className="space-y-2">
              {client.bank_accounts.map((ba) => (
                <div key={ba.id} className="flex items-center gap-4 text-sm border rounded-md p-3">
                  <span className="font-medium">{ba.bank_name}</span>
                  <span className="font-mono">{ba.account_number}</span>
                  {ba.ifsc_code && <span className="text-muted-foreground">{ba.ifsc_code}</span>}
                  {ba.is_primary && (
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">Primary</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Monthly Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Coming in Phase 2 - monthly reconciliation status will appear here.</p>
        </CardContent>
      </Card>

      {showAddBank && (
        <BankAccountAddModal
          clientId={clientId}
          onClose={() => setShowAddBank(false)}
          onCreated={() => {
            setShowAddBank(false);
            fetchClient();
          }}
        />
      )}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string | null | undefined; mono?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-xs" : ""}>{value || "-"}</span>
    </div>
  );
}
