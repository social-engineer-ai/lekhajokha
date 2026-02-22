"use client";

import { useCallback, useRef, useState } from "react";
import { apiUpload } from "@/lib/api";
import { Job } from "@/lib/types/bank";
import { Button } from "@/components/ui/button";

interface InvoiceUploadZoneProps {
  clientId: string;
  onUploadStarted: (jobs: Job[]) => void;
}

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
];
const ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"];
const MAX_FILES = 20;

function isAllowedFile(file: File): boolean {
  if (ALLOWED_TYPES.includes(file.type)) return true;
  const ext = file.name.toLowerCase().split(".").pop();
  return ext ? ALLOWED_EXTENSIONS.includes(`.${ext}`) : false;
}

export function InvoiceUploadZone({ clientId, onUploadStarted }: InvoiceUploadZoneProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [invoiceType, setInvoiceType] = useState<"auto" | "sales" | "purchase">("auto");
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const validFiles: File[] = [];
    for (const file of Array.from(newFiles)) {
      if (!isAllowedFile(file)) {
        setError(`"${file.name}" is not a supported file type. Use PDF, JPG, or PNG.`);
        return;
      }
      validFiles.push(file);
    }
    setFiles((prev) => {
      const combined = [...prev, ...validFiles];
      if (combined.length > MAX_FILES) {
        setError(`Maximum ${MAX_FILES} files allowed`);
        return prev;
      }
      return combined;
    });
    setError(null);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        addFiles(e.target.files);
      }
    },
    [addFiles]
  );

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }
      formData.append("invoice_type", invoiceType);

      const jobs = await apiUpload<Job[]>(
        `/clients/${clientId}/invoices/`,
        formData
      );
      onUploadStarted(jobs);
      setFiles([]);
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
          accept=".pdf,.jpg,.jpeg,.png"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        {files.length > 0 ? (
          <p className="text-sm font-medium">
            {files.length} file{files.length > 1 ? "s" : ""} selected
          </p>
        ) : (
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">
              Drop invoice files here or click to browse
            </p>
            <p className="text-xs text-muted-foreground">
              PDF, JPG, PNG — up to 20 files, 20MB each
            </p>
          </div>
        )}
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <div className="max-h-40 overflow-y-auto space-y-1">
            {files.map((file, i) => (
              <div
                key={`${file.name}-${i}`}
                className="flex items-center justify-between text-sm bg-muted/50 rounded px-3 py-1.5"
              >
                <span className="truncate flex-1 mr-2">{file.name}</span>
                <span className="text-xs text-muted-foreground mr-2">
                  {(file.size / 1024).toFixed(0)} KB
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(i);
                  }}
                  className="text-muted-foreground hover:text-destructive text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>

          <div className="flex items-end gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium">Type:</span>
              {(["auto", "sales", "purchase"] as const).map((type) => (
                <label key={type} className="flex items-center gap-1 text-xs cursor-pointer">
                  <input
                    type="radio"
                    name="invoiceType"
                    value={type}
                    checked={invoiceType === type}
                    onChange={() => setInvoiceType(type)}
                    className="accent-primary"
                  />
                  {type === "auto" ? "Auto-detect" : type.charAt(0).toUpperCase() + type.slice(1)}
                </label>
              ))}
            </div>

            <Button onClick={handleUpload} disabled={uploading} size="sm" className="ml-auto">
              {uploading ? "Uploading..." : `Upload ${files.length} file${files.length > 1 ? "s" : ""}`}
            </Button>
          </div>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
