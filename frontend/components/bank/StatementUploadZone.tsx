"use client";

import { useCallback, useRef, useState } from "react";
import { apiUpload } from "@/lib/api";
import { Job } from "@/lib/types/bank";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface StatementUploadZoneProps {
  clientId: string;
  bankAccountId: string;
  onUploadStarted: (job: Job) => void;
}

export function StatementUploadZone({
  clientId,
  bankAccountId,
  onUploadStarted,
}: StatementUploadZoneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === "application/pdf") {
      setFile(droppedFile);
      setError(null);
    } else {
      setError("Please drop a PDF file");
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setError(null);
    }
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("bank_account_id", bankAccountId);
      if (password) {
        formData.append("password", password);
      }

      const job = await apiUpload<Job>(
        `/clients/${clientId}/bank-statements/`,
        formData
      );
      onUploadStarted(job);
      setFile(null);
      setPassword("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileSelect}
          className="hidden"
        />
        {file ? (
          <div className="space-y-1">
            <p className="text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">
              Drop a bank statement PDF here or click to browse
            </p>
            <p className="text-xs text-muted-foreground">PDF files up to 20MB</p>
          </div>
        )}
      </div>

      {file && (
        <div className="flex items-end gap-3">
          <div className="flex-1 max-w-xs">
            <Label htmlFor="pdf-password" className="text-xs">
              PDF Password (if protected)
            </Label>
            <Input
              id="pdf-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Leave empty if not protected"
              className="h-8 text-sm"
            />
          </div>
          <Button onClick={handleUpload} disabled={uploading} size="sm">
            {uploading ? "Uploading..." : "Upload & Process"}
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
