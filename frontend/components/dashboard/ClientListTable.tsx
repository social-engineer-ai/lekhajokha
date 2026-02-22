"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface Client {
  id: string;
  business_name: string;
  gstin: string | null;
  city: string | null;
  contact_name: string | null;
  gst_filing_frequency: string;
  is_active: boolean;
}

interface ClientListTableProps {
  clients: Client[];
}

export function ClientListTable({ clients }: ClientListTableProps) {
  const [search, setSearch] = useState("");

  const filtered = clients.filter(
    (c) =>
      c.business_name.toLowerCase().includes(search.toLowerCase()) ||
      (c.gstin && c.gstin.includes(search.toUpperCase())) ||
      (c.city && c.city.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Input
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <Button asChild>
          <Link href="/dashboard/clients/new">Add Client</Link>
        </Button>
      </div>

      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left p-3 font-medium">Business Name</th>
              <th className="text-left p-3 font-medium">GSTIN</th>
              <th className="text-left p-3 font-medium">City</th>
              <th className="text-left p-3 font-medium">Contact</th>
              <th className="text-left p-3 font-medium">Filing</th>
              <th className="text-left p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">
                  {clients.length === 0
                    ? "No clients yet. Add your first client to get started."
                    : "No clients match your search."}
                </td>
              </tr>
            ) : (
              filtered.map((client) => (
                <tr key={client.id} className="border-b hover:bg-muted/30">
                  <td className="p-3 font-medium">
                    <Link href={`/dashboard/clients/${client.id}`} className="hover:underline text-primary">
                      {client.business_name}
                    </Link>
                  </td>
                  <td className="p-3 font-mono text-xs">{client.gstin || "-"}</td>
                  <td className="p-3">{client.city || "-"}</td>
                  <td className="p-3">{client.contact_name || "-"}</td>
                  <td className="p-3">
                    <Badge variant="secondary">{client.gst_filing_frequency}</Badge>
                  </td>
                  <td className="p-3">
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/dashboard/clients/${client.id}`}>Open</Link>
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
