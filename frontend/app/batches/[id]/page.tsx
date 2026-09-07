"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend, ApiError } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/Button";
import type { AppointmentOut, BatchDetail } from "@/lib/types";

const input =
  "w-full rounded-sm border border-borderstrong bg-surface px-2 py-1 text-13 outline-none focus:border-accent";

export default function BatchPage({ params }: { params: { id: string } }) {
  const id = params.id;
  const [batch, setBatch] = useState<BatchDetail | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<{ id: string; mode: "edit" | "verify" } | null>(null);

  const refresh = useCallback(() => {
    apiGet<BatchDetail>(`/admin/batches/${id}`).then(setBatch).catch(() => {});
  }, [id]);
  useEffect(refresh, [refresh]);

  async function act(path: string, body?: unknown) {
    setMsg(null);
    try {
      const res = await apiSend<Record<string, unknown>>(path, "POST", body);
      if (res && typeof res.report_url === "string") setReportUrl(res.report_url);
      setExpanded(null);
      refresh();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Something went wrong.");
    }
  }

  if (!batch) return <main className="mx-auto max-w-5xl px-6 py-10 text-14 text-ink3">Loading…</main>;

  const pending = batch.appointments.some((a) => a.verification_status === "pending");

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Link href="/queue" className="text-13 text-accent hover:underline">&larr; Queue</Link>

      <header className="mt-3 flex flex-wrap items-center justify-between gap-3 border-b border-ink pb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-22 font-semibold">Batch review</h1>
          <StatusBadge status={batch.status} />
        </div>
        <div className="flex items-center gap-2">
          {batch.status === "review" && (
            <Button onClick={() => act(`/admin/batches/${id}/start-verification`)}>
              Start verification
            </Button>
          )}
          {batch.status === "verifying" && (
            <Button disabled={pending} onClick={() => act(`/admin/batches/${id}/approve`)}>
              {pending ? "Resolve all to approve" : "Approve"}
            </Button>
          )}
          {batch.status === "ready" && (
            <Button onClick={() => act(`/admin/batches/${id}/send`)}>Send report</Button>
          )}
        </div>
      </header>

      {msg && (
        <p className="mt-4 rounded-sm border border-bad-bd bg-bad-bg px-3 py-2 text-13 text-bad-ink">{msg}</p>
      )}
      {reportUrl && (
        <p className="mt-4 rounded-sm border border-ok-bd bg-ok-bg px-3 py-2 text-13 text-ok-ink">
          Report sent. Secure link: <span className="break-all font-mono">{reportUrl}</span>
        </p>
      )}

      <div className="mt-5 overflow-hidden rounded-md border border-border bg-surface">
        <div className="grid grid-cols-[150px_1.4fr_1.2fr_110px] gap-3 border-b border-borderstrong bg-surfacealt px-4 py-2 text-11 font-semibold uppercase tracking-wide text-ink3">
          <div>Status</div><div>Patient</div><div>Payer / member</div><div></div>
        </div>
        {batch.appointments.map((a) => (
          <Row
            key={a.id}
            appt={a}
            batchStatus={batch.status}
            expanded={expanded?.id === a.id ? expanded.mode : null}
            onToggle={(mode) => setExpanded(expanded?.id === a.id && expanded.mode === mode ? null : { id: a.id, mode })}
            onSaved={() => { setExpanded(null); refresh(); }}
            onError={setMsg}
          />
        ))}
      </div>
    </main>
  );
}

function Row({
  appt, batchStatus, expanded, onToggle, onSaved, onError,
}: {
  appt: AppointmentOut;
  batchStatus: string;
  expanded: "edit" | "verify" | null;
  onToggle: (m: "edit" | "verify") => void;
  onSaved: () => void;
  onError: (m: string) => void;
}) {
  return (
    <div className="border-b border-border last:border-b-0">
      <div className="grid grid-cols-[150px_1.4fr_1.2fr_110px] items-center gap-3 px-4 py-2.5">
        <StatusBadge status={appt.verification_status} />
        <div>
          <div className="text-14 font-medium">{appt.patient_name ?? <span className="text-warn-ink">(missing name)</span>}</div>
          <div className="num text-12 text-ink3">{appt.dob ?? "no DOB"}</div>
        </div>
        <div className="text-13">
          <div>{appt.payer_name ?? <span className="text-warn-ink">missing payer</span>}</div>
          <div className="num text-12 text-ink3">{appt.subscriber_id ?? "no member ID"}</div>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={() => onToggle("edit")} className="text-13 text-accent hover:underline">Edit</button>
          {appt.verification_status === "pending" && (
            <button onClick={() => onToggle("verify")} className="text-13 font-medium text-accent hover:underline">Verify</button>
          )}
        </div>
      </div>
      {expanded === "edit" && <EditForm appt={appt} onSaved={onSaved} onError={onError} />}
      {expanded === "verify" && appt.verification_id && (
        <VerifyForm verificationId={appt.verification_id} onSaved={onSaved} onError={onError} />
      )}
      {batchStatus === "review" && appt.needs_review && expanded !== "edit" && (
        <div className="px-4 pb-2.5 text-12 text-warn-ink">Needs review before verification.</div>
      )}
    </div>
  );
}

function EditForm({ appt, onSaved, onError }: { appt: AppointmentOut; onSaved: () => void; onError: (m: string) => void }) {
  const [f, setF] = useState({
    patient_name: appt.patient_name ?? "",
    dob: appt.dob ?? "",
    payer_name: appt.payer_name ?? "",
    subscriber_id: appt.subscriber_id ?? "",
    payer_id: appt.payer_id ?? "",
  });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function save() {
    try {
      const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));
      await apiSend(`/admin/appointments/${appt.id}`, "PATCH", body);
      onSaved();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Save failed.");
    }
  }

  return (
    <div className="grid grid-cols-2 gap-3 bg-surfacealt px-4 py-3 sm:grid-cols-5">
      <L t="Name"><input className={input} value={f.patient_name} onChange={set("patient_name")} /></L>
      <L t="DOB (YYYY-MM-DD)"><input className={`${input} num`} value={f.dob} onChange={set("dob")} placeholder="1990-01-15" /></L>
      <L t="Payer"><input className={input} value={f.payer_name} onChange={set("payer_name")} /></L>
      <L t="Member ID"><input className={`${input} num`} value={f.subscriber_id} onChange={set("subscriber_id")} /></L>
      <L t="Payer ID"><input className={`${input} num`} value={f.payer_id} onChange={set("payer_id")} /></L>
      <div className="col-span-2 sm:col-span-5"><Button onClick={save} className="py-1.5">Save</Button></div>
    </div>
  );
}

function VerifyForm({ verificationId, onSaved, onError }: { verificationId: string; onSaved: () => void; onError: (m: string) => void }) {
  const [f, setF] = useState({
    status: "active", payer: "", plan: "", effective_date: "",
    annual_max: "", remaining_benefit: "", deductible_total: "", deductible_met: "", note: "",
  });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });

  async function save() {
    try {
      const body: Record<string, unknown> = { status: f.status };
      for (const k of ["payer", "plan", "effective_date", "annual_max", "remaining_benefit", "deductible_total", "deductible_met", "note"] as const) {
        if (f[k] !== "") body[k] = f[k];
      }
      await apiSend(`/admin/verifications/${verificationId}/resolve`, "POST", body);
      onSaved();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Resolve failed.");
    }
  }

  return (
    <div className="grid grid-cols-2 gap-3 bg-accent-weak px-4 py-3 sm:grid-cols-4">
      <L t="Coverage">
        <select className={input} value={f.status} onChange={set("status")}>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="needs_info">Needs info</option>
        </select>
      </L>
      <L t="Payer"><input className={input} value={f.payer} onChange={set("payer")} /></L>
      <L t="Plan"><input className={input} value={f.plan} onChange={set("plan")} /></L>
      <L t="Effective (YYYY-MM-DD)"><input className={`${input} num`} value={f.effective_date} onChange={set("effective_date")} /></L>
      <L t="Annual max"><input className={`${input} num`} value={f.annual_max} onChange={set("annual_max")} placeholder="1500.00" /></L>
      <L t="Remaining"><input className={`${input} num`} value={f.remaining_benefit} onChange={set("remaining_benefit")} placeholder="1200.00" /></L>
      <L t="Deductible total"><input className={`${input} num`} value={f.deductible_total} onChange={set("deductible_total")} /></L>
      <L t="Deductible met"><input className={`${input} num`} value={f.deductible_met} onChange={set("deductible_met")} /></L>
      <L t="Note"><input className={input} value={f.note} onChange={set("note")} /></L>
      <div className="col-span-2 sm:col-span-4"><Button onClick={save} className="py-1.5">Save verification</Button></div>
    </div>
  );
}

function L({ t, children }: { t: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-11 font-semibold uppercase tracking-wide text-ink3">{t}</span>
      {children}
    </label>
  );
}
