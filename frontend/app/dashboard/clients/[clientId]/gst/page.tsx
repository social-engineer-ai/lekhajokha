"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { GSTSummary, GSTR1Response, GSTR3BResponse } from "@/lib/types/gst";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { PeriodPicker } from "@/components/gst/PeriodPicker";
import { GSTSummaryCards } from "@/components/gst/GSTSummaryCards";
import { GSTR1View } from "@/components/gst/GSTR1View";
import { GSTR3BView } from "@/components/gst/GSTR3BView";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type GSTTab = "gstr1" | "gstr3b";

export default function GSTPage() {
  const params = useParams();
  const clientId = params.clientId as string;

  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [activeTab, setActiveTab] = useState<GSTTab>("gstr1");

  const [summary, setSummary] = useState<GSTSummary | null>(null);
  const [gstr1, setGstr1] = useState<GSTR1Response | null>(null);
  const [gstr3b, setGstr3b] = useState<GSTR3BResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const summaryData = await apiFetch<GSTSummary>(
        `/clients/${clientId}/gst/summary?month=${month}&year=${year}`
      );
      setSummary(summaryData);

      // Fetch the active tab data
      if (activeTab === "gstr1") {
        const data = await apiFetch<GSTR1Response>(
          `/clients/${clientId}/gst/gstr1`,
          { method: "POST", body: JSON.stringify({ month, year }) }
        );
        setGstr1(data);
      } else {
        const data = await apiFetch<GSTR3BResponse>(
          `/clients/${clientId}/gst/gstr3b`,
          { method: "POST", body: JSON.stringify({ month, year }) }
        );
        setGstr3b(data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [clientId, month, year, activeTab]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExportJSON = async () => {
    try {
      const endpoint = activeTab === "gstr1" ? "gstr1/export" : "gstr3b/export";
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/clients/${clientId}/gst/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ month, year }),
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${activeTab.toUpperCase()}_${month}_${year}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  };

  const tabs: { key: GSTTab; label: string }[] = [
    { key: "gstr1", label: "GSTR-1" },
    { key: "gstr3b", label: "GSTR-3B" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">GST Returns</h2>
          <p className="text-sm text-muted-foreground">
            Prepare GSTR-1 and GSTR-3B from invoice data
          </p>
        </div>
        <PeriodPicker month={month} year={year} onMonthChange={setMonth} onYearChange={setYear} />
      </div>

      {/* Summary cards */}
      {summary && <GSTSummaryCards summary={summary} />}

      <Separator />

      {/* Tabs + Export */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                activeTab === tab.key
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <Button variant="outline" size="sm" onClick={handleExportJSON}>
          Export JSON
        </Button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground">
          <p className="text-sm">Loading GST data...</p>
        </div>
      ) : (
        <>
          {activeTab === "gstr1" && gstr1 && <GSTR1View data={gstr1} />}
          {activeTab === "gstr3b" && gstr3b && <GSTR3BView data={gstr3b} />}
        </>
      )}
    </div>
  );
}
