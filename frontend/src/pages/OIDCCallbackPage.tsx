import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { handleOidcCallback } from "../lib/oidcClient";
import { authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";

export default function OIDCCallbackPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setTokens, setUser } = useAuthStore();
  const processed = useRef(false);
  const [statusMessage, setStatusMessage] = useState("Validating OIDC security token...");
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
          throw new Error("No id_token received from identity provider.");
        }

        setStatusMessage("Authenticating user session with Financial Hub Core...");
        const { data } = await authAPI.exchangeOidc(oidcUser.id_token);
        setTokens(data.access, data.refresh);
        setUser(data.user);

        setStatusMessage("Permissions verified. Launching workspace...");
        setTimeout(() => {
          navigate("/launcher", { replace: true });
        }, 350);
      } catch (err: any) {
        console.error("OIDC callback error:", err);
        setErrorMessage(
          err.message || "Failed to establish enterprise SSO session. Please return to login."
        );
      }
    })();
  }, [location.search, navigate, setTokens, setUser]);

  return (
    <div className="min-h-screen bg-[#f4f7fa] flex items-center justify-center p-6 text-[#1c2a3a]">
      <div className="w-full max-w-md bg-white border border-[#d4dce5] rounded-lg p-8 shadow-sm text-center">
        <span className="inline-block text-[10px] font-bold uppercase tracking-wider text-[#c71f37] bg-rose-50 px-2.5 py-1 rounded border border-rose-200 mb-3">
          SECURE SSO HANDSHAKE
        </span>
        <h2 className="text-xl font-bold text-[#182332] mb-4">Identity Federation Broker</h2>

        {errorMessage ? (
          <div>
            <div className="bg-red-50 border border-red-200 text-red-800 text-xs p-3 rounded-md mb-4 text-left">
              {errorMessage}
            </div>
            <button
              onClick={() => navigate("/login", { replace: true })}
              className="w-full py-2.5 px-4 bg-[#c71f37] hover:bg-[#a8172c] text-white text-xs font-semibold rounded shadow-sm"
            >
              Return to Login Portal
            </button>
          </div>
        ) : (
          <div className="py-6 space-y-3">
            <div className="w-8 h-8 border-2 border-slate-300 border-t-[#c71f37] rounded-full animate-spin mx-auto" />
            <p className="text-xs font-medium text-slate-700">{statusMessage}</p>
            <p className="text-[11px] text-slate-400">
              Single Sign-On assertion &amp; token exchange in progress
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
