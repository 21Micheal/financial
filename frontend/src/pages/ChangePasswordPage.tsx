import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authAPI } from "../services/api";
import { useAuthStore } from "../store/authStore";

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const user = useAuthStore((s) => s.user);

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (next !== confirm) {
      setError("New passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await authAPI.changePassword(current, next);
      if (user) setUser({ ...user, must_change_password: false });
      navigate("/launcher", { replace: true });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.join(" ") : detail || "Failed to change password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f7fa] flex items-center justify-center p-6 text-[#1c2a3a]">
      <div className="w-full max-w-md bg-white border border-[#d4dce5] rounded-lg p-8 shadow-sm">
        <span className="inline-block text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-2.5 py-1 rounded border border-blue-200 mb-2">
          ACCOUNT SECURITY
        </span>
        <h1 className="text-xl font-bold text-[#182332]">Change Password</h1>
        <p className="text-xs text-slate-500 mt-1 mb-5">
          You must set a new password before continuing to your workspace.
        </p>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-800 text-xs p-3 rounded-md">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Current Password
            </label>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm bg-white border border-[#d4dce5] rounded focus:outline-none focus:ring-2 focus:ring-[#c71f37] text-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              New Password (min 10 characters)
            </label>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm bg-white border border-[#d4dce5] rounded focus:outline-none focus:ring-2 focus:ring-[#c71f37] text-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm bg-white border border-[#d4dce5] rounded focus:outline-none focus:ring-2 focus:ring-[#c71f37] text-slate-900"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 bg-[#c71f37] hover:bg-[#a8172c] disabled:bg-slate-300 text-white font-semibold text-sm rounded shadow-sm transition-colors"
          >
            {loading ? "Saving..." : "Set New Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
