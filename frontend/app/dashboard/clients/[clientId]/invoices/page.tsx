"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Invoice } from "@/lib/types/invoice";
import { Job } from "@/lib/types/bank";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ProcessingIndicator } from "@/components/bank/ProcessingIndicator";
import { InvoiceUploadZone } from "@/components/invoices/InvoiceUploadZone";
import { InvoiceList } from "@/components/invoices/InvoiceList";

type FilterTab = "all" | "sales" | "purchase";

export default function InvoicesPage() {
  const params = useParams();
  const clientId = params.clientId as string;

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterTab, setFilterTab] = useState<FilterTab>("all");
  const [search, setSearch] = useState("");

  const loadInvoices = useCallback(async () => {
    try {
      let endpoint = `/clients/${clientId}/invoices/?page_size=200`;
      if (filterTab !== "all") {
        endpoint += `&invoice_type=${filterTab}`;
      }
      if (search) {
        endpoint += `&search=${encodeURIComponent(search)}`;
      }
      const data = await apiFetch<Invoice[]>(endpoint);
      setInvoices(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [clientId, filterTab, search]);

  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

  const handleUploadStarted = (jobs: Job[]) => {
    setActiveJobs((prev) => [...jobs, ...prev]);
  };

  const handleJobComplete = useCallback(() => {
    loadInvoices();
    // Clean up completed/failed jobs after a short delay
    setTimeout(() => {
      setActiveJobs((prev) =>
        prev.filter((j) => j.status === "pending" || j.status === "processing")
      );
    }, 3000);
  }, [loadInvoices]);

  const tabs: { key: FilterTab; label: string }[] = [
    { key: "all", label: "All" },
    { key: "sales", label: "Sales" },
    { key: "purchase", label: "Purchase" },
  ];

  return (
    <div className="space-y-4">
      {/* Filter tabs */}
      <div className="flex items-center gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilterTab(tab.key)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              filterTab === tab.key
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Upload zone */}
      <InvoiceUploadZone clientId={clientId} onUploadStarted={handleUploadStarted} />

      {/* Active processing jobs */}
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

      {/* Search */}
      <Input
        placeholder="Search by invoice #, seller, buyer, or GSTIN..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-md h-8 text-sm"
      />

      {/* Invoice list */}
      {loading ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          Loading invoices...
        </div>
      ) : (
        <InvoiceList
          invoices={invoices}
          clientId={clientId}
          onRefresh={loadInvoices}
        />
      )}
    </div>
  );
}
