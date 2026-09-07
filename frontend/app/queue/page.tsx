"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import type { BatchSummary } from "@/lib/types";

export default function QueuePage() {
  const [batches, setBatches] = useState<BatchSummary[] | null>(null);

  useEffect(() => {
    apiGet<BatchSummary[]>("/admin/batches").then(setBatches).catch(() => {});
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-6 flex items-baseline justify-between border-b border-ink pb-4">
        <div>
          <div className="text-11 font-semibold uppercase tracking-widest text-ink3">verifi-dental</div>
          <h1 className="mt-1 text-22 font-semibold">Review queue</h1>
        </div>
        <button
          onClick={() => apiSend("/admin/logout", "POST").finally(() => (window.location.href = "/login"))}
          className="text-13 text-accent hover:text-accent-hover hover:underline"
        >
          Sign out
        </button>
      </header>

      {batches === null ? (
        <p className="text-14 text-ink3">Loading…</p>
      ) : batches.length === 0 ? (
        <div className="rounded-md border border-border bg-surface p-8 text-center">
          <p className="text-15 font-medium">Nothing in the queue</p>
          <p className="mt-1 text-13 text-ink3">Uploaded schedules appear here for review.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-md border border-border bg-surface">
          {batches.map((b) => (
            <Link
              key={b.id}
              href={`/batches/${b.id}`}
              className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border px-4 py-3 last:border-b-0 hover:bg-accent-weak"
            >
              <div>
                <div className="text-15 font-medium">{b.practice_name}</div>
                <div className="num mt-0.5 text-12 text-ink3">
                  {b.appointments} patients
                  {b.needing_review > 0 && (
                    <> &middot; <span className="font-medium text-warn-ink">{b.needing_review} need review</span></>
                  )}
                </div>
              </div>
              <StatusBadge status={b.status} />
              <span className="text-14 font-medium text-accent">Open &rarr;</span>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
