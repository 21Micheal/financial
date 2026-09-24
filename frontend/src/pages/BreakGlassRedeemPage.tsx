import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";

export default function BreakGlassRedeemPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setTokens, setUser } = useAuthStore();
  const processed = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const params = new URLSearchParams(location.search);
    const token = params.get("token");

    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    authAPI
      .redeemBreakGlass(token)
      .then(({ data }) => {
        setTokens(data.access, data.refresh);
        setUser(data.user);
        navigate("/launcher", { replace: true });
      })
      .catch((err) => {
        setError(
          err.response?.data?.detail ||
            "Emergency access link is invalid or has expired. Please restart the process."
        );
      });
  }, [location.search, navigate, setTokens, setUser]);

  return (
    <div className="min-h-screen bg-[#0f172a] flex items-center justify-center p-6 text-slate-200">
      <div className="w-full max-w-sm bg-[#1e293b] border border-slate-700 rounded-lg p-8 text-center shadow-lg">
        <span className="inline-block text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-950/60 border border-amber-800/80 px-2.5 py-1 rounded mb-4">
          EMERGENCY ACCESS
        </span>

        {error ? (
          <div>
            <p className="text-xs text-red-300 mb-6 leading-relaxed">{error}</p>
            <button
              onClick={() => (window.location.href = "/operations/console")}
              className="w-full py-2.5 px-4 bg-amber-500 hover:bg-amber-400 text-slate-900 font-bold text-xs rounded transition-colors"
            >
              Return to Emergency Login
            </button>
          </div>
        ) : (
          <div className="py-4 space-y-3">
            <div className="w-6 h-6 border-2 border-slate-600 border-t-amber-400 rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-300">Establishing emergency session...</p>
          </div>
        )}
      </div>
    </div>
  );
}
