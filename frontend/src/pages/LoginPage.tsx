import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { oidcLogin } from "../lib/oidcClient";

export default function LoginPage() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  // Check for existing local session on mount (tab duplication)
  useEffect(() => {
    if (isAuthenticated) {
      // Already have valid local tokens, redirect to launcher
      navigate("/launcher");
    }
  }, [isAuthenticated, navigate]);

  const handleKeycloakLogin = async () => {
    setError("");
    setLoading(true);
    try {
      await oidcLogin();
    } catch {
      setError("Could not reach the identity provider. Please contact IT support.");
      setLoading(false);
    }
  };

  const handleMicrosoftLogin = async () => {
    setError("");
    setLoading(true);
    try {
      // Microsoft login via Keycloak identity provider
      await oidcLogin("microsoft");
    } catch {
      setError("Could not reach Microsoft identity provider. Please contact IT support.");
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#f5f8fb] text-[#11263f]">
      <section className="flex min-h-screen flex-col justify-between px-6 py-8 sm:px-12 sm:py-10 lg:px-16 xl:px-24">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#0b86c4] text-xs font-black tracking-[-0.12em] text-white">
              FSE
            </div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#0b6e9f]">
              Flaxem
            </p>
          </div>
          <p className="text-xs text-slate-500">
            Need help?{" "}
            <span className="font-semibold text-[#0b6e9f]">Contact IT support</span>
          </p>
        </header>

        <div className="mx-auto w-full max-w-[430px] py-12">
          <div className="mb-10">
            <p className="mb-4 text-[11px] font-bold uppercase tracking-[0.22em] text-[#0b86c4]">
              Financial systems hub
            </p>
            <h2 className="text-3xl font-semibold tracking-[-0.035em] text-[#11263f] sm:text-4xl">
              Welcome back.
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              Sign in to access your organization&apos;s connected business systems.
            </p>
          </div>

          {error && (
            <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          )}

          <div className="rounded-2xl border border-[#dfe8ee] bg-white p-6 shadow-[0_18px_55px_rgba(18,50,76,0.08)] sm:p-8">
            <div className="mb-6 flex items-center gap-3 rounded-xl bg-[#f1f8fb] px-4 py-3.5">
              <span
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[#d4eef5] text-[#0879a9]"
                aria-hidden="true"
              >
                ✓
              </span>
              <p className="text-xs leading-5 text-slate-600">
                Your organization uses secure single sign-on.
              </p>
            </div>

            <div className="space-y-3">
              <button
                type="button"
                onClick={handleKeycloakLogin}
                disabled={loading}
                className="flex w-full items-center justify-between rounded-xl bg-[#0a80bb] px-5 py-4 text-sm font-semibold text-white shadow-[0_7px_18px_rgba(10,128,187,0.22)] transition hover:bg-[#076d9f] disabled:cursor-wait disabled:opacity-60"
              >
                <span className="flex items-center gap-3">
                  <span
                    className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/15 text-xs"
                    aria-hidden="true"
                  >
                    →
                  </span>
                  {loading ? "Connecting…" : "Sign in via corporate SSO"}
                </span>
                <span className="text-lg text-white/60">›</span>
              </button>

              <button
                type="button"
                onClick={handleMicrosoftLogin}
                disabled={loading}
                className="flex w-full items-center justify-between rounded-xl border border-[#d9e4ea] bg-white px-5 py-4 text-sm font-semibold text-[#18344e] transition hover:border-[#9fc8da] hover:bg-[#f8fbfc] disabled:cursor-wait disabled:opacity-60"
              >
                <span className="flex items-center gap-3">
                  <span
                    className="grid h-7 w-7 grid-cols-2 gap-0.5 p-1"
                    aria-hidden="true"
                  >
                    <i className="bg-[#f35325]" />
                    <i className="bg-[#81bc06]" />
                    <i className="bg-[#05a6f0]" />
                    <i className="bg-[#ffba08]" />
                  </span>
                  {loading ? "Connecting…" : "Continue with Microsoft"}
                </span>
                <span className="text-lg text-slate-300">›</span>
              </button>
            </div>

            <div className="mt-7 flex items-start gap-3 border-t border-[#edf1f3] pt-5 text-[11px] leading-5 text-slate-400">
              <span className="mt-0.5 text-[#0b86c4]" aria-hidden="true">
                ▣
              </span>
              <p>
                Access is managed by your organization. You may be redirected to
                your identity provider to complete sign-in.
              </p>
            </div>
          </div>
        </div>

        <footer className="flex flex-col gap-2 text-[11px] text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Flaxem System Enterprises Ltd.</p>
          <p className="flex gap-4">
            <span>Privacy</span>
            <span>Security</span>
          </p>
        </footer>
      </section>
    </main>
  );
}