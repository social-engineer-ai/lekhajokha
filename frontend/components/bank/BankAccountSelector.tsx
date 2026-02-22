"use client";

import { BankAccount } from "@/lib/types/bank";

interface BankAccountSelectorProps {
  accounts: BankAccount[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function BankAccountSelector({ accounts, selectedId, onSelect }: BankAccountSelectorProps) {
  if (accounts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No bank accounts found. Add a bank account first in the Overview tab.
      </p>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <label htmlFor="bank-account-select" className="text-sm font-medium whitespace-nowrap">
        Bank Account
      </label>
      <select
        id="bank-account-select"
        value={selectedId || ""}
        onChange={(e) => onSelect(e.target.value)}
        className="flex h-9 w-full max-w-sm rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        <option value="">Select bank account...</option>
        {accounts.map((acc) => (
          <option key={acc.id} value={acc.id}>
            {acc.bank_name} - ****{acc.account_number.slice(-4)} ({acc.account_type})
            {acc.is_primary ? " [Primary]" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
