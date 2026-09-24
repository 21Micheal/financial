import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { launcherAPI } from "../services/api";
import "./LauncherPage.css";

type AccessStatus = "ready" | "not_provisioned" | "unavailable";

interface LicensedSystem {
  system: string;
  display: string;
  description: string;
  info_url: string;
  public_url: string;
  licensed: boolean;
  expires_at: string | null;
  status: AccessStatus;
  access_message: string | null;
}

const STATUS_LABEL: Record<AccessStatus, string> = {
  ready: "Ready to open",
  not_provisioned: "Account not set up",
  unavailable: "Unavailable",
};

// "FSE DMS (Document Management System)" -> "FD"
function initials(name: string): string {
  const words = name
    .replace(/\(.*?\)/g, "")
    .split(/[\s–-]+/)
    .filter(Boolean);
  return words
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export default function LauncherPage() {
  const [systems, setSystems] = useState<LicensedSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSystem, setSelectedSystem] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState<"ALL" | AccessStatus>("ALL");

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

  const handleSystemClick = async (system: LicensedSystem) => {
    if (redirecting || system.status !== "ready") return;

    setSelectedSystem(system.system);
    setRedirecting(true);
    setError("");

    try {
      const { data } = await launcherAPI.initiateSSO(system.system);
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
          "Failed to open the system"
      );
      setRedirecting(false);
      setSelectedSystem(null);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const filteredSystems = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return systems.filter((system) => {
      const matchesFilter = selectedFilter === "ALL" || system.status === selectedFilter;
      const matchesQuery = !query || `${system.display} ${system.description}`.toLowerCase().includes(query);
      return matchesFilter && matchesQuery;
    });
  }, [searchQuery, selectedFilter, systems]);

  const readyCount = systems.filter((system) => system.status === "ready").length;
  const unavailableCount = systems.filter((system) => system.status === "unavailable").length;

  return (
    <div className="launcher-page">
      <header className="launcher-header">
        <div className="header-content">
          <div className="brand-lockup">
            <span className="brand-mark" aria-hidden="true">F</span>
            <div>
              <span className="brand-eyebrow">FLAXEM PLATFORM</span>
              <h1>Financial Systems Hub</h1>
            </div>
          </div>
          <div className="user-info">
            <div className="user-copy">
              <strong>{user?.first_name} {user?.last_name}</strong>
              <span>Authenticated workspace</span>
            </div>
            <button onClick={handleLogout} className="logout-button">Sign out</button>
          </div>
        </div>
      </header>

      <main className="launcher-main">
        <section className="workspace-intro">
          <div>
            <span className="section-kicker">YOUR LICENSED PRODUCTS</span>
            <h2>Everything your organization can access</h2>
            <p>Launch provisioned services or see what still needs administrator attention.</p>
          </div>
          <div className="workspace-health">
            <span className="health-dot" />
            <span>Live access checks</span>
          </div>
        </section>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        <section className="dashboard-summary" aria-label="License summary">
          <div className="summary-tile">
            <span className="summary-label">Licensed products</span>
            <strong>{systems.length}</strong>
            <span className="summary-note">Current organization access</span>
          </div>
          <div className="summary-tile summary-tile-ready">
            <span className="summary-label">Ready to launch</span>
            <strong>{readyCount}</strong>
            <span className="summary-note">Provisioning confirmed live</span>
          </div>
          <div className="summary-tile summary-tile-attention">
            <span className="summary-label">Needs attention</span>
            <strong>{systems.length - readyCount}</strong>
            <span className="summary-note">Not provisioned or unavailable</span>
          </div>
          <div className="summary-tile">
            <span className="summary-label">Unavailable</span>
            <strong>{unavailableCount}</strong>
            <span className="summary-note">Integration response required</span>
          </div>
        </section>

        <section className="systems-section">
          <div className="systems-toolbar">
            <label className="search-box">
              <span className="sr-only">Search licensed products</span>
              <span aria-hidden="true">⌕</span>
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search products"
              />
            </label>
            <div className="filter-group" role="group" aria-label="Filter products">
              {(["ALL", "ready", "not_provisioned", "unavailable"] as const).map((filter) => (
                <button
                  key={filter}
                  className={selectedFilter === filter ? "filter-button active" : "filter-button"}
                  onClick={() => setSelectedFilter(filter)}
                >
                  {filter === "ALL" ? "All" : STATUS_LABEL[filter]}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="loading">Loading licensed products...</div>
          ) : (
            <div className="systems-grid">
            {filteredSystems.map((system) => {
            const ready = system.status === "ready";
            return (
              <div
                key={system.system}
                role="button"
                tabIndex={ready ? 0 : -1}
                aria-disabled={!ready}
                className={`system-card status-${system.status} ${
                  selectedSystem === system.system ? "selected" : ""
                }`}
                onClick={() => handleSystemClick(system)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSystemClick(system);
                  }
                }}
              >
                <div className="system-card-topline">
                  <div className="system-avatar" aria-hidden="true">{initials(system.display)}</div>
                  <span className={`system-status-dot ${system.status}`} />
                </div>
                <span className="system-status-label">{STATUS_LABEL[system.status]}</span>
                <h3>{system.display}</h3>
                {system.description && (
                  <p className="system-description">{system.description}</p>
                )}
                <span className={`launch-action ${ready ? "launch-action-ready" : ""}`}>
                  {redirecting && selectedSystem === system.system ? "Opening..." : ready ? "Launch product" : "Access restricted"}
                </span>
                {!ready && system.access_message && (
                  <div className="access-denied">{system.access_message}</div>
                )}
                {system.expires_at && (
                  <p className="license-expiry">
                    Licence expires{" "}
                    {new Date(system.expires_at).toLocaleDateString()}
                  </p>
                )}
                {system.info_url && (
                  <a
                    className="info-link"
                    href={system.info_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    About this product
                  </a>
                )}
              </div>
            );
            })}
            </div>
          )}

        {!loading && filteredSystems.length === 0 && !error && (
          <div className="no-systems">
            <strong>No products match this view.</strong>
            <p>Try a different search or filter, or contact your administrator.</p>
          </div>
        )}
        </section>
      </main>
    </div>
  );
}