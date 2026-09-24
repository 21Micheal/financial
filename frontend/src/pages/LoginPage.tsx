import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { configAPI, authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";
import { oidcLogin } from "../lib/oidcClient";
import CustomListbox from "../components/ui/CustomListbox";
import "./LoginPage.css";

const ENVIRONMENTS = [
  { value: "PRD", label: "Production (PRD-FIN01)" },
  { value: "UAT", label: "User Acceptance (UAT-STG)" },
  { value: "DEV", label: "Sandbox / Dev (DEV-SYS)" },
];

export default function LoginPage() {
  const [authMode, setAuthMode] = useState<"keycloak" | "native">("native");
  const [environment, setEnvironment] = useState("PRD");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"credentials" | "otp">("credentials");
  const [userId, setUserId] = useState<string | null>(null);

  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const { data } = await configAPI.getConfig();
        setAuthMode(data.auth_mode);
      } catch (err) {
        console.error("Failed to fetch config:", err);
      }
    };
    fetchConfig();
  }, []);

  const handleKeycloakLogin = async () => {
    setError("");
    setLoading(true);
    try {
      await oidcLogin();
    } catch {
      setError("Could not reach the Keycloak Identity Provider. Please contact IT support.");
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
      setError(err.response?.data?.detail || "Authentication failed. Check your corporate credentials.");
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
      setError(err.response?.data?.detail || "Security OTP verification failed. Token expired or invalid.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="erp-login-page">
      {/* Left Brand / Hub Architecture Panel */}
      <div className="erp-login-brand-panel">
        <div className="brand-header">
          <div className="brand-logo-mark">
            <span className="logo-symbol">◆</span>
            <span className="logo-title">INFOR <span className="logo-light">FINANCIAL HUB</span></span>
          </div>
          <span className="system-release-tag">v2026.4 Enterprise</span>
        </div>

        <div className="brand-hero">
          <h2>Unified Hub & Spoke Financial Architecture</h2>
          <p className="hero-subtext">
            Enterprise orchestration bridging SunSystems General Ledger, Infor Q&A Vision, and IDM DocuSign operations.
          </p>

          <div className="spoke-ecosystem-preview">
            <div className="spoke-preview-item active">
              <div className="spoke-icon">📑</div>
              <div className="spoke-info">
                <strong>Infor SunSystems</strong>
                <span>Multi-currency Journals, Ledger Inquiries & Analysis</span>
              </div>
            </div>
            <div className="spoke-preview-item">
              <div className="spoke-icon">✍️</div>
              <div className="spoke-info">
                <strong>IDM / DocuSign Dashboard</strong>
                <span>Automated Document Routing & Authorizations</span>
              </div>
            </div>
            <div className="spoke-preview-item">
              <div className="spoke-icon">📊</div>
              <div className="spoke-info">
                <strong>Infor Q&A (Vision)</strong>
                <span>Real-time Financial Data Delivery & Extraction</span>
              </div>
            </div>
          </div>
        </div>

        <div className="brand-footer">
          <span>Protected by Enterprise Dual-Factor Token Validation</span>
          <span className="audit-code">ISO 27001 & SOC 2 Type II Certified</span>
        </div>
      </div>

      {/* Right Authentication Container */}
      <div className="erp-login-form-panel">
        <div className="login-card">
          <div className="login-card-header">
            <div className="portal-badge">FINANCIAL CORE GATEWAY</div>
            <h1>Corporate Sign In</h1>
            <p>Access your designated SunSystems business units and spoke microservices.</p>
          </div>

          <div className="env-selector-wrapper">
            <label className="input-label">Target Financial Environment</label>
            <CustomListbox
              value={environment}
              onChange={setEnvironment}
              options={ENVIRONMENTS}
              className="w-full"
              buttonClassName="env-listbox-btn"
            />
          </div>

          {error && (
            <div className="erp-alert erp-alert-danger" role="alert">
              <span className="alert-icon">⚠</span>
              <div className="alert-text">{error}</div>
            </div>
          )}

          {authMode === "keycloak" ? (
            <div className="keycloak-action-container">
              <p className="sso-instructions">
                Your organization enforces Single Sign-On (SSO) via enterprise Keycloak IDP.
              </p>
              <button
                type="button"
                onClick={handleKeycloakLogin}
                className="erp-btn erp-btn-primary w-full"
                disabled={loading}
              >
                {loading ? (
                  <span className="loading-spinner-inline" />
                ) : (
                  <span className="btn-icon">🔒</span>
                )}
                {loading ? "Connecting to Identity Gateway..." : "Sign in via Corporate SSO (Keycloak)"}
              </button>
            </div>
          ) : step === "credentials" ? (
            <form onSubmit={handleNativeLogin} className="erp-form">
              <div className="form-group">
                <label htmlFor="email" className="input-label">Corporate Email Address</label>
                <div className="input-with-icon">
                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="name@organization.com"
                    className="erp-input"
                    autoComplete="username"
                  />
                </div>
              </div>

              <div className="form-group">
                <div className="label-row">
                  <label htmlFor="password" className="input-label">Password</label>
                  <span className="help-link">Forgot password?</span>
                </div>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="erp-input"
                  autoComplete="current-password"
                />
              </div>

              <button type="submit" disabled={loading} className="erp-btn erp-btn-primary w-full">
                {loading ? "Authenticating..." : "Continue with Credentials"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleOTPVerification} className="erp-form">
              <div className="otp-step-header">
                <span className="otp-icon">✉</span>
                <p>A 6-digit security code was dispatched to <strong>{email}</strong></p>
              </div>

              <div className="form-group">
                <label htmlFor="otp" className="input-label">Security OTP Code</label>
                <input
                  type="text"
                  id="otp"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  maxLength={6}
                  required
                  placeholder="000000"
                  className="erp-input erp-otp-input"
                  autoFocus
                />
              </div>

              <button type="submit" disabled={loading || otp.length < 6} className="erp-btn erp-btn-primary w-full">
                {loading ? "Validating Token..." : "Confirm & Enter Hub"}
              </button>

              <button
                type="button"
                onClick={() => setStep("credentials")}
                className="erp-btn erp-btn-secondary w-full"
                disabled={loading}
              >
                ← Return to Credentials
              </button>
            </form>
          )}

          <div className="login-card-footer">
            <p>Session activity is logged and monitored under financial audit compliance.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
