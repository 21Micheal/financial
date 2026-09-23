import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { launcherAPI } from "../services/api";
import "./LauncherPage.css";

interface LicensedSystem {
  system: string;
  display: string;
  public_url: string;
  licensed: boolean;
  provisioned: boolean;
  access_message?: string | null;
}

export default function LauncherPage() {
  const [systems, setSystems] = useState<LicensedSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSystem, setSelectedSystem] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  useEffect(() => {
    const fetchSystems = async () => {
      try {
        const { data } = await launcherAPI.getLicensedSystems();
        setSystems(data.systems);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load systems");
        if (err.response?.status === 401) {
          logout();
          navigate("/login");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchSystems();
  }, [navigate, logout]);

  const handleSystemClick = async (system: string) => {
    if (redirecting) return;

    const systemData = systems.find((s) => s.system === system);
    if (!systemData) return;

    if (!systemData.provisioned) {
      setError(
        systemData.access_message ||
          "Your organization is licensed, but your account has not been provisioned. Contact your administrator."
      );
      return;
    }

    setSelectedSystem(system);
    setRedirecting(true);
    setError("");

    try {
      const { data } = await launcherAPI.initiateSSO(system);
      if (!data.redirect_url) {
        setError(data.access_message || "Access denied");
        setRedirecting(false);
        setSelectedSystem(null);
        return;
      }
      window.location.href = data.redirect_url;
    } catch (err: any) {
      setError(
        err.response?.data?.access_message ||
          err.response?.data?.detail ||
          "Failed to initiate SSO"
      );
      setRedirecting(false);
      setSelectedSystem(null);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (loading) {
    return (
      <div className="launcher-page">
        <div className="loading">Loading systems...</div>
      </div>
    );
  }

  return (
    <div className="launcher-page">
      <header className="launcher-header">
        <div className="header-content">
          <h1>Financial System Launcher</h1>
          <div className="user-info">
            <span>
              {user?.first_name} {user?.last_name}
            </span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="launcher-main">
        {error && <div className="error-message">{error}</div>}

        <div className="systems-grid">
          {systems.map((system) => (
            <div
              key={system.system}
              className={`system-card ${!system.provisioned ? "blocked" : ""} ${
                selectedSystem === system.system ? "selected" : ""
              }`}
              onClick={() => !redirecting && handleSystemClick(system.system)}
            >
              <div className="system-icon">
                {system.system === "dms" && "📄"}
                {system.system === "inventory" && "📦"}
              </div>
              <h3>{system.display}</h3>
              {system.provisioned ? (
                <p className="user-role">Ready — click to open</p>
              ) : (
                <p className="no-role">Licensed, not provisioned</p>
              )}
              {!system.provisioned && (
                <div className="access-denied">
                  {system.access_message ||
                    "Contact your administrator for access"}
                </div>
              )}
              {redirecting && selectedSystem === system.system && (
                <div className="redirecting">Redirecting...</div>
              )}
            </div>
          ))}
        </div>

        {systems.length === 0 && !error && (
          <div className="no-systems">
            <p>No systems are currently licensed for your organization.</p>
            <p>Contact your administrator to add system licenses.</p>
          </div>
        )}
      </main>
    </div>
  );
}
