"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { BankAccount, BankStatement, Job } from "@/lib/types/bank";
import { BankAccountSelector } from "@/components/bank/BankAccountSelector";
import { StatementUploadZone } from "@/components/bank/StatementUploadZone";
import { ProcessingIndicator } from "@/components/bank/ProcessingIndicator";
import { StatementList } from "@/components/bank/StatementList";
import { TransactionTable } from "@/components/bank/TransactionTable";
import { Separator } from "@/components/ui/separator";

export default function BankPage() {
  const params = useParams();
  const clientId = params.clientId as string;

  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [statements, setStatements] = useState<BankStatement[]>([]);
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch bank accounts
  useEffect(() => {
    apiFetch<BankAccount[]>(`/clients/${clientId}/bank-accounts/`)
      .then((data) => {
        const active = data.filter((a) => a.is_active);
        setAccounts(active);
        if (active.length > 0) {
          setSelectedAccountId((prev) => {
            if (prev) return prev;
            const primary = active.find((a) => a.is_primary);
            return primary?.id || active[0].id;
          });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [clientId]);

  // Fetch statements when account changes
  const fetchStatements = useCallback(async () => {
    if (!selectedAccountId) return;
    try {
      const data = await apiFetch<BankStatement[]>(
        `/clients/${clientId}/bank-statements/?bank_account_id=${selectedAccountId}`
      );
      setStatements(data);
    } catch {
      // Silently handle
    }
  }, [clientId, selectedAccountId]);

  useEffect(() => {
    fetchStatements();
  }, [fetchStatements]);

  const handleUploadStarted = (job: Job) => {
    setActiveJobs((prev) => [job, ...prev]);
  };

  const handleJobComplete = useCallback(() => {
    fetchStatements();
    // Clean up completed jobs after a delay
    setTimeout(() => {
      setActiveJobs((prev) => prev.filter((j) => j.status !== "completed" && j.status !== "failed"));
    }, 5000);
  }, [fetchStatements]);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading bank data...</p>;
  }

  return (
    <div className="space-y-6">
      {/* Bank Account Selector */}
      <BankAccountSelector
        accounts={accounts}
        selectedId={selectedAccountId}
        onSelect={setSelectedAccountId}
      />

      {selectedAccountId && (
        <>
          {/* Upload Zone */}
          <StatementUploadZone
            clientId={clientId}
            bankAccountId={selectedAccountId}
            onUploadStarted={handleUploadStarted}
          />

          {/* Active Processing Jobs */}
          {activeJobs.length > 0 && (
            <div className="space-y-2">
              {activeJobs.map((job) => (
                <ProcessingIndicator
                  key={job.id}
                  job={job}
                  onComplete={handleJobComplete}
                />
              ))}
            </div>
          )}

          <Separator />

          {/* Statement List */}
          <StatementList statements={statements} />

          <Separator />

          {/* Transaction Table */}
          <TransactionTable
            clientId={clientId}
            bankAccountId={selectedAccountId}
          />
        </>
      )}
    </div>
  );
}
