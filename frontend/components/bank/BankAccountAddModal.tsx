"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface BankAccountAddModalProps {
  clientId: string;
  onClose: () => void;
  onCreated: () => void;
}

export function BankAccountAddModal({ clientId, onClose, onCreated }: BankAccountAddModalProps) {
  const [bankName, setBankName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [ifscCode, setIfscCode] = useState("");
  const [branchName, setBranchName] = useState("");
  const [accountType, setAccountType] = useState("current");
  const [isPrimary, setIsPrimary] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bankName.trim()) {
      setError("Bank name is required");
      return;
    }
    if (!accountNumber.trim()) {
      setError("Account number is required");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await apiFetch(`/clients/${clientId}/bank-accounts/`, {
        method: "POST",
        body: JSON.stringify({
          bank_name: bankName.trim(),
          account_number: accountNumber.trim(),
          ifsc_code: ifscCode.trim() || null,
          branch_name: branchName.trim() || null,
          account_type: accountType,
          is_primary: isPrimary,
        }),
      });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add bank account");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Add Bank Account</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="bank-name">Bank Name *</Label>
            <Input
              id="bank-name"
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
              placeholder="e.g. HDFC Bank"
              required
            />
          </div>
          <div>
            <Label htmlFor="account-number">Account Number *</Label>
            <Input
              id="account-number"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              placeholder="e.g. 50100123456789"
              required
            />
          </div>
          <div>
            <Label htmlFor="ifsc-code">IFSC Code</Label>
            <Input
              id="ifsc-code"
              value={ifscCode}
              onChange={(e) => setIfscCode(e.target.value)}
              placeholder="e.g. HDFC0001234"
              maxLength={11}
            />
          </div>
          <div>
            <Label htmlFor="branch-name">Branch Name</Label>
            <Input
              id="branch-name"
              value={branchName}
              onChange={(e) => setBranchName(e.target.value)}
              placeholder="e.g. Koramangala Branch"
            />
          </div>
          <div>
            <Label htmlFor="account-type">Account Type</Label>
            <select
              id="account-type"
              value={accountType}
              onChange={(e) => setAccountType(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="current">Current</option>
              <option value="savings">Savings</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="is-primary"
              type="checkbox"
              checked={isPrimary}
              onChange={(e) => setIsPrimary(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <Label htmlFor="is-primary" className="cursor-pointer">Set as primary account</Label>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Adding..." : "Add Account"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
