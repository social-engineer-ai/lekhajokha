"use client";

import { BankAccount } from "@/lib/types/bank";

interface BankAccountSelectorProps {
  accounts: BankAccount[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAddAccount?: () => void;
}

export function BankAccountSelector({ accounts, selectedId, onSelect, onAddAccount }: BankAccountSelectorProps) {
  if (accounts.length === 0) {
    return (
      <div className="flex items-center gap-3">
        <p className="text-sm text-muted-foreground">
          No bank accounts found.
        </p>
        {onAddAccount ? (
          <button
            onClick={onAddAccount}
            className="text-sm text-primary hover:underline font-medium"
          >
            + Add Account
          </button>
        ) : (
          <span className="text-sm text-muted-foreground">Add a bank account first in the Overview tab.</span>
        )}
      </div>
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
