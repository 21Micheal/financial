import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";
import { oidcLogin } from "../lib/oidcClient";

// Resolved at Vite build time from VITE_AUTH_MODE env var.
// Defaults to "native" so local dev with no .env still works.
const AUTH_MODE = (import.meta.env.VITE_AUTH_MODE ?? "native") as "keycloak" | "native";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"credentials" | "otp">("credentials");
  const [userId, setUserId] = useState<string | null>(null);

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

  const handleNativeLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await authAPI.login(email, password);
      setUserId(data.user_id);
      setStep("otp");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Authentication failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleOTPVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await authAPI.verifyOTP(userId!, otp);
      setTokens(data.access, data.refresh);
      setUser(data.user);
      navigate("/launcher");
    } catch (err: any) {
      setError(err.response?.data?.detail || "OTP verification failed. Code may be expired or invalid.");
    } finally {
      setLoading(false);
    }
  };

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

        {AUTH_MODE === "keycloak" ? (
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
        ) : step === "credentials" ? (
          <form onSubmit={handleNativeLogin} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-700 mb-1">
                Corporate Email
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="name@organisation.com"
                autoComplete="username"
                className="w-full px-3 py-2 text-sm bg-white border border-[#d4dce5] rounded focus:outline-none focus:ring-2 focus:ring-[#0066b3] focus:border-transparent text-slate-900"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-700 mb-1">
                Password
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••••••"
                autoComplete="current-password"
                className="w-full px-3 py-2 text-sm bg-white border border-[#d4dce5] rounded focus:outline-none focus:ring-2 focus:ring-[#0066b3] focus:border-transparent text-slate-900"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-[#0066b3] hover:bg-[#00508c] disabled:bg-slate-300 text-white font-semibold text-sm rounded shadow-sm transition-colors"
            >
              {loading ? "Authenticating..." : "Continue with Credentials"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleOTPVerification} className="space-y-4">
            <div className="text-center p-2 text-xs text-slate-600">
              <span className="text-2xl block mb-1">✉</span>
              <p>
                A 6-digit verification code was sent to <strong>{email}</strong>
              </p>
            </div>

            <div>
              <label htmlFor="otp" className="block text-xs font-semibold text-slate-700 mb-1">
                Security OTP Code
              </label>
              <input
                type="text"
                id="otp"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                maxLength={6}
                required
                placeholder="000000"
                autoFocus
                inputMode="numeric"
                className="w-full px-3 py-2 text-lg text-center font-bold tracking-widest bg-white border border-[#d4dce5] rounded focus:outline-none focus:ring-2 focus:ring-[#0066b3] focus:border-transparent text-slate-900"
              />
            </div>

            <button
              type="submit"
              disabled={loading || otp.length < 6}
              className="w-full py-2.5 px-4 bg-[#0066b3] hover:bg-[#00508c] disabled:bg-slate-300 text-white font-semibold text-sm rounded shadow-sm transition-colors"
            >
              {loading ? "Validating..." : "Confirm & Enter Hub"}
            </button>

            <button
              type="button"
              onClick={() => setStep("credentials")}
              disabled={loading}
              className="w-full py-2 text-xs text-slate-600 hover:text-slate-900 border border-slate-300 hover:bg-slate-50 rounded transition-colors"
            >
              ← Return to Credentials
            </button>
          </form>
        )}
      </main>

      {/* ── Footer / Copyright ───────────────────────────────────────── */}
      <footer className="w-full max-w-md pb-4 text-center text-xs text-slate-500">
        <p>© 2026 Flaxem System Enterprises Ltd. All rights reserved.</p>
      </footer>
    </div>
  );
}
