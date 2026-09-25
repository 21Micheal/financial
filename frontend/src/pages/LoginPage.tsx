import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { oidcLogin } from "../lib/oidcClient";

export default function LoginPage() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();

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

  // Auto-redirect to Keycloak on mount
  useEffect(() => {
    handleKeycloakLogin();
  }, []);

  return (
    <div className="min-h-screen w-full bg-white flex flex-col justify-between items-center p-6 sm:p-10 text-[#1c2a3a]">
      {/* ── Top Brand Bar ────────────────────────────────────────────── */}
      <header className="w-full max-w-md pt-4 flex items-center justify-center gap-2.5">
        <span className="w-8 h-8 rounded bg-[#0066b3] text-white flex items-center justify-center font-bold text-sm shadow-sm">
          F
        </span>
        <div className="text-left">
          <span className="text-[10px] uppercase font-bold tracking-widest text-[#0066b3] block">
            FLAXEM PLATFORM
          </span>
          <span className="text-base font-bold tracking-tight text-[#182332] block">
            Financial Systems Hub
          </span>
        </div>
      </header>

      {/* ── Main Form Card ───────────────────────────────────────────── */}
      <main className="w-full max-w-md bg-white border border-[#d4dce5] rounded-lg p-8 sm:p-10 shadow-sm my-8">
        <div className="mb-6 text-center">
          <span className="inline-block text-[10px] font-bold uppercase tracking-wider text-[#0066b3] bg-blue-50 px-2.5 py-1 rounded border border-blue-200 mb-2">
            FINANCIAL CORE GATEWAY
          </span>
          <h1 className="text-2xl font-bold text-[#182332]">Corporate Sign In</h1>
          <p className="text-xs text-slate-500 mt-1">
            Access your organization's financial services and spokes.
          </p>
        </div>

        {error && (
          <div className="mb-5 bg-red-50 border border-red-200 text-red-800 text-xs p-3 rounded-md flex items-start gap-2">
            <span className="text-sm font-bold">⚠</span>
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-4">
          <p className="text-xs text-slate-600 text-center leading-relaxed">
            Your organization enforces Single Sign-On (SSO). Sign in via your corporate identity provider.
          </p>
          <button
            type="button"
            onClick={handleKeycloakLogin}
            disabled={loading}
            className="w-full py-2.5 px-4 bg-[#0066b3] hover:bg-[#00508c] disabled:bg-slate-300 text-white font-semibold text-sm rounded shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <span>🔒</span>
                Sign in via Corporate SSO
              </>
            )}
          </button>
        </div>
      </main>

      {/* ── Footer / Copyright ───────────────────────────────────────── */}
      <footer className="w-full max-w-md pb-4 text-center text-xs text-slate-500">
        <p>© 2026 Flaxem System Enterprises Ltd. All rights reserved.</p>
      </footer>
    </div>
  );
}
