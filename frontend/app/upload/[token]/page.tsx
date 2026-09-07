"use client";

import { useState } from "react";
import { apiUpload } from "@/lib/api";
import { Button } from "@/components/Button";
import type { UploadResponse } from "@/lib/types";
import { CheckIcon } from "@/components/icons";

export default function UploadPage({ params }: { params: { token: string } }) {
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await apiUpload<UploadResponse>(`/upload/${params.token}`, file));
    } catch {
      setError("We couldn't accept that upload. The link may have expired — please request a new one.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <div className="text-11 font-semibold uppercase tracking-widest text-ink3">verifi-dental</div>
      <h1 className="mt-1 text-22 font-semibold">Send tomorrow&rsquo;s schedule</h1>
      <p className="mt-1 max-w-prose text-14 text-ink2">
        Upload your appointment list — CSV, Excel, or a PDF/printout of the schedule. We&rsquo;ll
        verify each patient&rsquo;s insurance and send back a clean report before you open.
      </p>

      {result ? (
        <div className="mt-8 rounded-md border border-ok-bd bg-ok-bg p-5">
          <div className="flex items-center gap-2 text-ok-ink">
            <CheckIcon className="h-5 w-5" />
            <span className="text-15 font-semibold">Received — thank you</span>
          </div>
          <p className="mt-2 text-14 text-ink2">
            We read <b className="num">{result.rows_parsed}</b> appointments
            {result.rows_needing_review > 0 && (
              <> (<b className="num">{result.rows_needing_review}</b> need a closer look on our end)</>
            )}
            . Your report will arrive by email before your day starts.
          </p>
        </div>
      ) : (
        <>
          <label
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); setFile(e.dataTransfer.files?.[0] ?? null); }}
            className={`mt-8 flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-12 text-center transition-colors ${
              drag ? "border-accent bg-accent-weak" : "border-borderstrong bg-surface"
            }`}
          >
            <input type="file" className="hidden"
              accept=".csv,.tsv,.xlsx,.xlsm,.pdf,.png,.jpg,.jpeg,.tif,.tiff"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <div className="text-14 font-medium">
              {file ? file.name : "Drop your file here, or click to choose"}
            </div>
            <div className="mt-1 text-12 text-ink3">CSV, Excel, PDF, or an image of the schedule</div>
          </label>

          {error && (
            <p className="mt-4 rounded-sm border border-bad-bd bg-bad-bg px-3 py-2 text-13 text-bad-ink">
              {error}
            </p>
          )}

          <div className="mt-5">
            <Button onClick={submit} disabled={!file || busy} className="py-2">
              {busy ? "Uploading…" : "Send to verifi"}
            </Button>
          </div>
          <p className="mt-6 text-12 text-ink3">
            This is a secure, single-use link. Do not forward it. No patient information is sent by email.
          </p>
        </>
      )}
    </main>
  );
}
