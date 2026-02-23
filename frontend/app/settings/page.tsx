"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { TallyConfig, TallyConnectionTest } from "@/lib/types/tally";
import {
  MessagingConfig,
  MessageTemplate,
  TestMessageResponse,
} from "@/lib/types/messaging";
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
import { NotificationTemplateList } from "@/components/messages/NotificationTemplateList";

export default function SettingsPage() {
  // ── Tally state ──
  const [tallyConfig, setTallyConfig] = useState<TallyConfig | null>(null);
  const [host, setHost] = useState("http://localhost");
  const [port, setPort] = useState("9000");
  const [companyName, setCompanyName] = useState("");
  const [tallySaving, setTallySaving] = useState(false);
  const [tallyTesting, setTallyTesting] = useState(false);
  const [tallyTestResult, setTallyTestResult] =
    useState<TallyConnectionTest | null>(null);
  const [tallySaveMsg, setTallySaveMsg] = useState("");

  // ── Messaging state ──
  const [msgConfig, setMsgConfig] = useState<MessagingConfig | null>(null);
  const [waEnabled, setWaEnabled] = useState(false);
  const [twilioSid, setTwilioSid] = useState("");
  const [twilioToken, setTwilioToken] = useState("");
  const [twilioNumber, setTwilioNumber] = useState("");
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFromEmail, setSmtpFromEmail] = useState("");
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [msgSaving, setMsgSaving] = useState(false);
  const [msgSaveMsg, setMsgSaveMsg] = useState("");
  const [waTestPhone, setWaTestPhone] = useState("");
  const [waTesting, setWaTesting] = useState(false);
  const [waTestResult, setWaTestResult] = useState<TestMessageResponse | null>(
    null
  );
  const [emailTestAddr, setEmailTestAddr] = useState("");
  const [emailTesting, setEmailTesting] = useState(false);
  const [emailTestResult, setEmailTestResult] =
    useState<TestMessageResponse | null>(null);

  // ── Templates ──
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [showTemplates, setShowTemplates] = useState(false);

  useEffect(() => {
    // Load Tally config
    (async () => {
      try {
        const data = await apiFetch<TallyConfig>("/tally/config");
        setTallyConfig(data);
        setHost(data.tally_host);
        setPort(String(data.tally_port));
        setCompanyName(data.company_name || "");
      } catch {
        // ignore
      }
    })();

    // Load Messaging config
    (async () => {
      try {
        const data = await apiFetch<MessagingConfig>("/messaging/config");
        setMsgConfig(data);
        setWaEnabled(data.whatsapp_enabled);
        setTwilioSid(data.twilio_account_sid || "");
        setTwilioNumber(data.twilio_whatsapp_number || "");
        setEmailEnabled(data.email_enabled);
        setSmtpHost(data.smtp_host || "");
        setSmtpPort(String(data.smtp_port));
        setSmtpUsername(data.smtp_username || "");
        setSmtpFromEmail(data.smtp_from_email || "");
        setSmtpUseTls(data.smtp_use_tls);
      } catch {
        // ignore
      }
    })();

    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await apiFetch<MessageTemplate[]>("/messaging/templates");
      setTemplates(data);
    } catch {
      // ignore
    }
  };

  // ── Tally handlers ──
  const handleTallySave = async () => {
    setTallySaving(true);
    setTallySaveMsg("");
    try {
      const updated = await apiFetch<TallyConfig>("/tally/config", {
        method: "PUT",
        body: JSON.stringify({
          tally_host: host,
          tally_port: Number(port),
          company_name: companyName || null,
        }),
      });
      setTallyConfig(updated);
      setTallySaveMsg("Settings saved");
    } catch {
      setTallySaveMsg("Failed to save");
    } finally {
      setTallySaving(false);
    }
  };

  const handleTallyTest = async () => {
    setTallyTesting(true);
    setTallyTestResult(null);
    try {
      const result = await apiFetch<TallyConnectionTest>(
        "/tally/test-connection",
        { method: "POST" }
      );
      setTallyTestResult(result);
      if (result.connected) {
        const updated = await apiFetch<TallyConfig>("/tally/config");
        setTallyConfig(updated);
        if (result.company_name) setCompanyName(result.company_name);
      }
    } catch {
      setTallyTestResult({
        connected: false,
        company_name: null,
        error: "Request failed",
      });
    } finally {
      setTallyTesting(false);
    }
  };

  // ── Messaging handlers ──
  const handleMsgSave = async () => {
    setMsgSaving(true);
    setMsgSaveMsg("");
    try {
      const payload: Record<string, unknown> = {
        whatsapp_enabled: waEnabled,
        email_enabled: emailEnabled,
        twilio_account_sid: twilioSid || null,
        twilio_whatsapp_number: twilioNumber || null,
        smtp_host: smtpHost || null,
        smtp_port: Number(smtpPort),
        smtp_username: smtpUsername || null,
        smtp_from_email: smtpFromEmail || null,
        smtp_use_tls: smtpUseTls,
      };
      // Only send password fields if user entered something
      if (twilioToken) payload.twilio_auth_token = twilioToken;
      if (smtpPassword) payload.smtp_password = smtpPassword;

      const updated = await apiFetch<MessagingConfig>("/messaging/config", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setMsgConfig(updated);
      setMsgSaveMsg("Messaging settings saved");
      setTwilioToken("");
      setSmtpPassword("");
    } catch {
      setMsgSaveMsg("Failed to save");
    } finally {
      setMsgSaving(false);
    }
  };

  const handleWaTest = async () => {
    if (!waTestPhone) return;
    setWaTesting(true);
    setWaTestResult(null);
    try {
      const result = await apiFetch<TestMessageResponse>(
        "/messaging/test-whatsapp",
        {
          method: "POST",
          body: JSON.stringify({ to: waTestPhone }),
        }
      );
      setWaTestResult(result);
    } catch {
      setWaTestResult({ success: false, message: null, error: "Request failed" });
    } finally {
      setWaTesting(false);
    }
  };

  const handleEmailTest = async () => {
    if (!emailTestAddr) return;
    setEmailTesting(true);
    setEmailTestResult(null);
    try {
      const result = await apiFetch<TestMessageResponse>(
        "/messaging/test-email",
        {
          method: "POST",
          body: JSON.stringify({ to: emailTestAddr }),
        }
      );
      setEmailTestResult(result);
    } catch {
      setEmailTestResult({
        success: false,
        message: null,
        error: "Request failed",
      });
    } finally {
      setEmailTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* ── Tally Connection ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Tally Connection</CardTitle>
              <CardDescription>
                Configure Tally Prime ERP connection for voucher sync
              </CardDescription>
            </div>
            {tallyConfig && (
              <Badge
                variant={tallyConfig.is_connected ? "default" : "secondary"}
              >
                {tallyConfig.is_connected ? "Connected" : "Not Connected"}
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
          {tallyConfig?.last_sync_at && (
            <p className="text-xs text-muted-foreground">
              Last sync:{" "}
              {new Date(tallyConfig.last_sync_at).toLocaleString("en-IN", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </p>
          )}
          {tallyTestResult && (
            <div
              className={`text-sm p-3 rounded-md ${
                tallyTestResult.connected
                  ? "bg-green-50 text-green-800 border border-green-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {tallyTestResult.connected
                ? `Connected to Tally${
                    tallyTestResult.company_name
                      ? ` — ${tallyTestResult.company_name}`
                      : ""
                  }`
                : tallyTestResult.error || "Connection failed"}
            </div>
          )}
          {tallySaveMsg && (
            <p className="text-sm text-muted-foreground">{tallySaveMsg}</p>
          )}
          <div className="flex gap-2">
            <Button onClick={handleTallySave} disabled={tallySaving}>
              {tallySaving ? "Saving..." : "Save Settings"}
            </Button>
            <Button
              variant="outline"
              onClick={handleTallyTest}
              disabled={tallyTesting}
            >
              {tallyTesting ? "Testing..." : "Test Connection"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ── WhatsApp Integration ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>WhatsApp Integration</CardTitle>
              <CardDescription>
                Configure Twilio WhatsApp Business API
              </CardDescription>
            </div>
            <Badge variant={waEnabled ? "default" : "secondary"}>
              {waEnabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="wa-enabled"
              checked={waEnabled}
              onChange={(e) => setWaEnabled(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="wa-enabled">Enable WhatsApp notifications</Label>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="twilio-sid">Twilio Account SID</Label>
              <Input
                id="twilio-sid"
                value={twilioSid}
                onChange={(e) => setTwilioSid(e.target.value)}
                placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="twilio-token">Auth Token</Label>
              <Input
                id="twilio-token"
                type="password"
                value={twilioToken}
                onChange={(e) => setTwilioToken(e.target.value)}
                placeholder="Enter to update (never shown)"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="twilio-number">WhatsApp Number</Label>
            <Input
              id="twilio-number"
              value={twilioNumber}
              onChange={(e) => setTwilioNumber(e.target.value)}
              placeholder="+14155238886"
            />
          </div>
          <div className="flex items-center gap-2">
            <Input
              value={waTestPhone}
              onChange={(e) => setWaTestPhone(e.target.value)}
              placeholder="Phone number to test"
              className="max-w-xs"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleWaTest}
              disabled={waTesting || !waTestPhone}
            >
              {waTesting ? "Sending..." : "Send Test"}
            </Button>
          </div>
          {waTestResult && (
            <div
              className={`text-sm p-3 rounded-md ${
                waTestResult.success
                  ? "bg-green-50 text-green-800 border border-green-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {waTestResult.success
                ? waTestResult.message
                : waTestResult.error || "Test failed"}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Email Integration ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Email Integration</CardTitle>
              <CardDescription>Configure SMTP for email notifications</CardDescription>
            </div>
            <Badge variant={emailEnabled ? "default" : "secondary"}>
              {emailEnabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="email-enabled"
              checked={emailEnabled}
              onChange={(e) => setEmailEnabled(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="email-enabled">Enable email notifications</Label>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="smtp-host">SMTP Host</Label>
              <Input
                id="smtp-host"
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="smtp-port">Port</Label>
              <Input
                id="smtp-port"
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(e.target.value)}
                placeholder="587"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="smtp-username">Username</Label>
              <Input
                id="smtp-username"
                value={smtpUsername}
                onChange={(e) => setSmtpUsername(e.target.value)}
                placeholder="your@email.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="smtp-password">Password</Label>
              <Input
                id="smtp-password"
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder="Enter to update (never shown)"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="smtp-from">From Email</Label>
              <Input
                id="smtp-from"
                value={smtpFromEmail}
                onChange={(e) => setSmtpFromEmail(e.target.value)}
                placeholder="noreply@yourdomain.com"
              />
            </div>
            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="smtp-tls"
                checked={smtpUseTls}
                onChange={(e) => setSmtpUseTls(e.target.checked)}
                className="rounded"
              />
              <Label htmlFor="smtp-tls">Use TLS</Label>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Input
              value={emailTestAddr}
              onChange={(e) => setEmailTestAddr(e.target.value)}
              placeholder="Email address to test"
              className="max-w-xs"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleEmailTest}
              disabled={emailTesting || !emailTestAddr}
            >
              {emailTesting ? "Sending..." : "Send Test"}
            </Button>
          </div>
          {emailTestResult && (
            <div
              className={`text-sm p-3 rounded-md ${
                emailTestResult.success
                  ? "bg-green-50 text-green-800 border border-green-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {emailTestResult.success
                ? emailTestResult.message
                : emailTestResult.error || "Test failed"}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Save Messaging Button ── */}
      <div className="flex items-center gap-3">
        <Button onClick={handleMsgSave} disabled={msgSaving}>
          {msgSaving ? "Saving..." : "Save Messaging Settings"}
        </Button>
        {msgSaveMsg && (
          <span className="text-sm text-muted-foreground">{msgSaveMsg}</span>
        )}
      </div>

      {/* ── Notification Templates ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Notification Templates</CardTitle>
              <CardDescription>
                Customize automated notification messages for each trigger event
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowTemplates(!showTemplates)}
            >
              {showTemplates ? "Collapse" : "Expand"}
            </Button>
          </div>
        </CardHeader>
        {showTemplates && (
          <CardContent>
            {templates.length > 0 ? (
              <NotificationTemplateList
                templates={templates}
                onUpdate={loadTemplates}
              />
            ) : (
              <p className="text-muted-foreground text-sm">
                No templates found. They will be created when the database is
                migrated.
              </p>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
