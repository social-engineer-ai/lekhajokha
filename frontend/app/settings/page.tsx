"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { TallyConfig, TallyConnectionTest } from "@/lib/types/tally";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

export default function SettingsPage() {
  const [config, setConfig] = useState<TallyConfig | null>(null);
  const [host, setHost] = useState("http://localhost");
  const [port, setPort] = useState("9000");
  const [companyName, setCompanyName] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TallyConnectionTest | null>(null);
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch<TallyConfig>("/tally/config");
        setConfig(data);
        setHost(data.tally_host);
        setPort(String(data.tally_port));
        setCompanyName(data.company_name || "");
      } catch {
        // ignore
      }
    })();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg("");
    try {
      const updated = await apiFetch<TallyConfig>("/tally/config", {
        method: "PUT",
        body: JSON.stringify({
          tally_host: host,
          tally_port: Number(port),
          company_name: companyName || null,
        }),
      });
      setConfig(updated);
      setSaveMsg("Settings saved");
    } catch {
      setSaveMsg("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await apiFetch<TallyConnectionTest>("/tally/test-connection", {
        method: "POST",
      });
      setTestResult(result);
      if (result.connected) {
        // Refresh config to get updated connection status
        const updated = await apiFetch<TallyConfig>("/tally/config");
        setConfig(updated);
        if (result.company_name) {
          setCompanyName(result.company_name);
        }
      }
    } catch {
      setTestResult({ connected: false, company_name: null, error: "Request failed" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Tally Connection</CardTitle>
              <CardDescription>
                Configure Tally Prime ERP connection for voucher sync
              </CardDescription>
            </div>
            {config && (
              <Badge variant={config.is_connected ? "default" : "secondary"}>
                {config.is_connected ? "Connected" : "Not Connected"}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tally-host">Tally Host</Label>
              <Input
                id="tally-host"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="http://localhost"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tally-port">Port</Label>
              <Input
                id="tally-port"
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="9000"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="company-name">Company Name</Label>
            <Input
              id="company-name"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Auto-detected on test connection"
            />
          </div>

          {config?.last_sync_at && (
            <p className="text-xs text-muted-foreground">
              Last sync:{" "}
              {new Date(config.last_sync_at).toLocaleString("en-IN", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </p>
          )}

          {testResult && (
            <div
              className={`text-sm p-3 rounded-md ${
                testResult.connected
                  ? "bg-green-50 text-green-800 border border-green-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {testResult.connected
                ? `Connected to Tally${testResult.company_name ? ` — ${testResult.company_name}` : ""}`
                : testResult.error || "Connection failed"}
            </div>
          )}

          {saveMsg && (
            <p className="text-sm text-muted-foreground">{saveMsg}</p>
          )}

          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save Settings"}
            </Button>
            <Button variant="outline" onClick={handleTest} disabled={testing}>
              {testing ? "Testing..." : "Test Connection"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>WhatsApp Integration</CardTitle>
          <CardDescription>
            Set up WhatsApp Business API - coming soon
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            WhatsApp Business API configuration will be available here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
