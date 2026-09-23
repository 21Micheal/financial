import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { handleOidcCallback } from "../lib/oidcClient";
import { authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";

export default function OIDCCallbackPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setTokens, setUser } = useAuthStore();
  const processed = useRef(false);

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

        const oidcUser = await handleOidcCallback();
        if (!oidcUser?.id_token) {
          throw new Error("No id_token returned from Keycloak.");
        }

        const { data } = await authAPI.exchangeOidc(oidcUser.id_token);
        setTokens(data.access, data.refresh);
        setUser(data.user);
        navigate("/launcher", { replace: true });
      } catch (err) {
        console.error("OIDC callback error:", err);
        navigate("/login", { replace: true });
      }
    })();
  }, [location.search, navigate, setTokens, setUser]);

  return (
    <div className="login-page">
      <div className="login-container">
        <p>Completing sign-in…</p>
      </div>
    </div>
  );
}
