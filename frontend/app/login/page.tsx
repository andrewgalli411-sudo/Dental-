"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiSend } from "@/lib/api";
import { Button } from "@/components/Button";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiSend("/admin/login", "POST", { email, password, totp });
      router.push("/queue");
    } catch {
      setError("Invalid email, password, or authentication code.");
      setBusy(false);
    }
  }

  const field =
    "w-full rounded-sm border border-borderstrong bg-surface px-3 py-2 text-14 outline-none focus:border-accent";
  const label = "block text-11 font-semibold uppercase tracking-wide text-ink3 mb-1.5";

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <div className="mb-8">
        <div className="text-11 font-semibold uppercase tracking-widest text-ink3">
          verifi-dental
        </div>
        <h1 className="mt-1 text-22 font-semibold">Admin sign in</h1>
        <p className="mt-1 text-13 text-ink2">
          Access to patient eligibility data requires your password and authenticator code.
        </p>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div>
          <label className={label} htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="username" className={field}
            value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className={label} htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" className={field}
            value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div>
          <label className={label} htmlFor="totp">Authenticator code</label>
          <input id="totp" inputMode="numeric" autoComplete="one-time-code"
            className={`${field} num tracking-widest`} value={totp}
            onChange={(e) => setTotp(e.target.value)} placeholder="123456" required />
        </div>
        {error && (
          <p className="rounded-sm border border-bad-bd bg-bad-bg px-3 py-2 text-13 text-bad-ink">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy} className="mt-1 py-2">
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </main>
  );
}
