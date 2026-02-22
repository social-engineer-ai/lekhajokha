"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Transaction } from "@/lib/types/bank";
import { TransactionRow } from "./TransactionRow";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface TransactionTableProps {
  clientId: string;
  bankAccountId: string | null;
}

const MODES = ["NEFT", "UPI", "IMPS", "RTGS", "ACH", "CHEQUE", "ATM", "INTERNAL"];

export function TransactionTable({ clientId, bankAccountId }: TransactionTableProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [modeFilter, setModeFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (bankAccountId) params.set("bank_account_id", bankAccountId);
      if (search) params.set("search", search);
      if (typeFilter) params.set("transaction_type", typeFilter);
      if (modeFilter) params.set("transaction_mode", modeFilter);
      params.set("page", String(page));
      params.set("page_size", String(pageSize));

      const data = await apiFetch<Transaction[]>(
        `/clients/${clientId}/transactions/?${params.toString()}`
      );
      setTransactions(data);
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, [clientId, bankAccountId, search, typeFilter, modeFilter, page]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  // Reset page on filter change
  useEffect(() => {
    setPage(1);
  }, [search, typeFilter, modeFilter, bankAccountId]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium">Transactions</h3>
        <Button variant="ghost" size="sm" onClick={fetchTransactions} className="h-6 text-xs">
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search description..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 text-xs w-48"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="h-8 rounded-md border border-input bg-transparent px-2 text-xs"
        >
          <option value="">All Types</option>
          <option value="debit">Debit (Dr)</option>
          <option value="credit">Credit (Cr)</option>
        </select>
        <select
          value={modeFilter}
          onChange={(e) => setModeFilter(e.target.value)}
          className="h-8 rounded-md border border-input bg-transparent px-2 text-xs"
        >
          <option value="">All Modes</option>
          {MODES.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-sm text-muted-foreground py-4">Loading transactions...</p>
      ) : transactions.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">No transactions found.</p>
      ) : (
        <>
          <div className="rounded-md border overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left p-2 font-medium text-xs">Date</th>
                  <th className="text-left p-2 font-medium text-xs">Description</th>
                  <th className="text-left p-2 font-medium text-xs">Mode</th>
                  <th className="text-right p-2 font-medium text-xs">Amount</th>
                  <th className="text-right p-2 font-medium text-xs">Balance</th>
                  <th className="text-left p-2 font-medium text-xs">Status</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => (
                  <TransactionRow key={txn.id} transaction={txn} />
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Showing {transactions.length} transactions (page {page})
            </p>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="h-7 text-xs"
              >
                Previous
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={transactions.length < pageSize}
                className="h-7 text-xs"
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
