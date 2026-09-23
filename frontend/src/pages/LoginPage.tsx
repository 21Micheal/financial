import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { configAPI, authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";
import { oidcLogin } from "../lib/oidcClient";
import "./LoginPage.css";

export default function LoginPage() {
  const [authMode, setAuthMode] = useState<"keycloak" | "native">("native");
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
      setError("Could not reach the identity provider. Please try again.");
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
      setError(err.response?.data?.detail || "Login failed");
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
      setError(err.response?.data?.detail || "OTP verification failed");
    } finally {
      setLoading(false);
    }
  };

  if (authMode === "keycloak") {
    return (
      <div className="login-page">
        <div className="login-container">
          <h1>Financial System</h1>
          <p>Sign in to access your organization's systems</p>
          {error && <div className="error-message">{error}</div>}
          <button onClick={handleKeycloakLogin} className="keycloak-button" disabled={loading}>
            {loading ? "Redirecting…" : "Sign in with Keycloak"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Financial System</h1>
        <p>Sign in to access your organization's systems</p>

        {error && <div className="error-message">{error}</div>}

        {step === "credentials" ? (
          <form onSubmit={handleNativeLogin}>
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? "Sending..." : "Request OTP"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleOTPVerification}>
            <div className="form-group">
              <label htmlFor="otp">Enter OTP sent to your email</label>
              <input
                type="text"
                id="otp"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                maxLength={6}
                required
                placeholder="123456"
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? "Verifying..." : "Verify & Login"}
            </button>
            <button
              type="button"
              onClick={() => setStep("credentials")}
              className="back-button"
            >
              Back
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
