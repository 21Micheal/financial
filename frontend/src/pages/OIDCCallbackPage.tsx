import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { handleOidcCallback } from "../lib/oidcClient";
import { authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";
import "./LoginPage.css";

export default function OIDCCallbackPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setTokens, setUser } = useAuthStore();
  const processed = useRef(false);
  const [statusMessage, setStatusMessage] = useState("Validating Keycloak OIDC security token...");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    (async () => {
      try {
        const params = new URLSearchParams(location.search);
        if (!params.has("code") && !params.has("state")) {
          navigate("/login", { replace: true });
          return;
        }

        setStatusMessage("Exchanging authorization code with Identity Gateway...");
        const oidcUser = await handleOidcCallback();
        if (!oidcUser?.id_token) {
          throw new Error("No id_token received from Keycloak identity provider.");
        }

        setStatusMessage("Authenticating user session with Financial Hub Core...");
        const { data } = await authAPI.exchangeOidc(oidcUser.id_token);
        setTokens(data.access, data.refresh);
        setUser(data.user);
        
        setStatusMessage("Permissions verified. Launching workspace...");
        setTimeout(() => {
          navigate("/launcher", { replace: true });
        }, 400);
      } catch (err: any) {
        console.error("OIDC callback error:", err);
        setErrorMessage(
          err.message || "Failed to establish enterprise SSO session. Please return to login."
        );
      }
    })();
  }, [location.search, navigate, setTokens, setUser]);

  return (
    <div className="erp-login-page" style={{ justifyContent: "center", alignItems: "center" }}>
      <div className="login-card" style={{ maxWidth: "460px", textAlign: "center" }}>
        <div className="portal-badge">SECURE SSO HANDSHAKE</div>
        <h2 style={{ fontSize: "1.35rem", color: "#182332", margin: "0.5rem 0 1rem 0" }}>
          Infor Federation Broker
        </h2>

        {errorMessage ? (
          <div>
            <div className="erp-alert erp-alert-danger" role="alert">
              <span className="alert-icon">⚠</span>
              <div className="alert-text">{errorMessage}</div>
            </div>
            <button
              onClick={() => navigate("/login", { replace: true })}
              className="erp-btn erp-btn-primary w-full"
            >
              Return to Login Portal
            </button>
          </div>
        ) : (
          <div>
            <div className="erp-spinner" style={{ margin: "1.5rem auto" }} />
            <p style={{ fontSize: "0.9rem", color: "#465870", fontWeight: 500 }}>
              {statusMessage}
            </p>
            <p style={{ fontSize: "0.75rem", color: "#8899ac", marginTop: "1rem" }}>
              Mutual TLS & Single Sign-On token assertion in progress
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
