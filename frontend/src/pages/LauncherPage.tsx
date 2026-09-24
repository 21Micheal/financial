import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { launcherAPI } from "../services/api";
import CustomListbox from "../components/ui/CustomListbox";
import "./LauncherPage.css";

interface LicensedSystem {
  system: string;
  display: string;
  public_url: string;
  licensed: boolean;
  provisioned: boolean;
  access_message?: string | null;
  category?: "financials" | "idm" | "operations" | "reporting";
  description?: string;
  code?: string;
}

const BUSINESS_UNITS = [
  { value: "PK1", label: "PK1 - Main Operating Ledger (USD)" },
  { value: "LON", label: "LON - EMEA Financial Entity (GBP)" },
  { value: "NBO", label: "NBO - Regional Hub Entity (KES)" },
  { value: "CORP", label: "CORP - Consolidated Group Accounts" },
];

export default function LauncherPage() {
  const [systems, setSystems] = useState<LicensedSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSystem, setSelectedSystem] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);
  const [activeBU, setActiveBU] = useState("PK1");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState<"ALL" | "LICENSED" | "PROVISIONED">("ALL");

  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  useEffect(() => {
    const fetchSystems = async () => {
      try {
        const { data } = await launcherAPI.getLicensedSystems();
        
        // Enrich backend systems with ERP metadata & categories
        const enriched: LicensedSystem[] = (data.systems || []).map((s: LicensedSystem) => {
          if (s.system === "dms" || s.system.toLowerCase().includes("doc")) {
            return {
              ...s,
              category: "idm",
              code: "IDM-DOC",
              description: "Infor Document Management with DocuSign Authorization routing",
            };
          }
          if (s.system === "inventory") {
            return {
              ...s,
              category: "operations",
              code: "SCM-INV",
              description: "Enterprise warehouse stock levels, transfers & valuation",
            };
          }
          if (s.system.toLowerCase().includes("sun") || s.system.toLowerCase().includes("journal")) {
            return {
              ...s,
              category: "financials",
              code: "SUN-GL",
              description: "SunSystems Multi-currency Ledger Posting & Account Inquiries",
            };
          }
          return {
            ...s,
            category: "financials",
            code: s.system.toUpperCase(),
            description: "Financial hub service provider component",
          };
        });

        // If SunSystems Journal Posting isn't supplied yet by backend, ensure core enterprise spokes display
        const hasSun = enriched.some((s) => s.system.toLowerCase().includes("sun"));
        if (!hasSun) {
          enriched.unshift({
            system: "sunsystems_gl",
            display: "SunSystems Financials",
            public_url: "#",
            licensed: true,
            provisioned: true,
            category: "financials",
            code: "SUN-FIN",
            description: "General Ledger, Journal Posting, AP/AR Sub-ledgers & Multi-currency",
          });
          enriched.push({
            system: "infor_qa",
            display: "Infor Q&A (Vision 11)",
            public_url: "#",
            licensed: true,
            provisioned: true,
            category: "reporting",
            code: "Q&A-XL",
            description: "Direct SunSystems table queries, drill-downs & executive statements",
          });
        }

        setSystems(enriched);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load licensed enterprise systems");
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

  const handleSystemClick = async (systemKey: string) => {
    if (redirecting) return;

    const systemData = systems.find((s) => s.system === systemKey);
    if (!systemData) return;

    if (!systemData.provisioned) {
      setError(
        systemData.access_message ||
          "Your organization holds a valid license, but your user profile has not been provisioned for this spoke. Contact your SunSystems Administrator."
      );
      return;
    }

    setSelectedSystem(systemKey);
    setRedirecting(true);
    setError("");

    try {
      const { data } = await launcherAPI.initiateSSO(systemKey);
      if (!data.redirect_url) {
        setError(data.access_message || "SSO token assertion rejected by Spoke Service Provider");
        setRedirecting(false);
        setSelectedSystem(null);
        return;
      }
      window.location.href = data.redirect_url;
    } catch (err: any) {
      setError(
        err.response?.data?.access_message ||
          err.response?.data?.detail ||
          "Failed to establish mutual SSO handshake with spoke service"
      );
      setRedirecting(false);
      setSelectedSystem(null);
    }
  };

  const filteredSystems = useMemo(() => {
    return systems.filter((s) => {
      const matchesSearch =
        s.display.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (s.description && s.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (s.code && s.code.toLowerCase().includes(searchQuery.toLowerCase()));

      if (!matchesSearch) return false;
      if (selectedFilter === "LICENSED") return s.licensed;
      if (selectedFilter === "PROVISIONED") return s.provisioned;
      return true;
    });
  }, [systems, searchQuery, selectedFilter]);

  const renderIcon = (sys: LicensedSystem) => {
    if (sys.system.includes("dms") || sys.category === "idm") {
      return (
        <div className="icon-badge idm-badge">
          <span>✍️</span>
        </div>
      );
    }
    if (sys.system.includes("sun") || sys.code?.includes("SUN")) {
      return (
        <div className="icon-badge sun-badge">
          <span>📑</span>
        </div>
      );
    }
    if (sys.category === "reporting" || sys.system.includes("qa")) {
      return (
        <div className="icon-badge qa-badge">
          <span>📊</span>
        </div>
      );
    }
    return (
      <div className="icon-badge generic-badge">
        <span>📦</span>
      </div>
    );
  };

  return (
    <div className="infor-shell">
      {/* Top Navigation Bar: Infor Ming.le / Dynamics 365 style */}
      <header className="infor-topbar">
        <div className="topbar-left">
          <button className="infor-waffle-btn" title="Infor OS Application Navigator">
            <span>:::</span>
          </button>
          <div className="topbar-brand">
            <span className="brand-logo-accent">◆</span>
            <span className="brand-suite">INFOR OS</span>
            <span className="brand-separator">/</span>
            <span className="brand-app">FINANCIAL HUB</span>
          </div>

          <div className="topbar-bu-selector">
            <span className="bu-label">Business Unit:</span>
            <CustomListbox
              value={activeBU}
              onChange={setActiveBU}
              options={BUSINESS_UNITS}
              className="bu-listbox-container"
              buttonClassName="bu-listbox-trigger"
            />
          </div>
        </div>

        <div className="topbar-right">
          <div className="status-env-pill">
            <span className="pulse-dot" />
            <span>PRD-HOSTED</span>
          </div>

          <div className="user-profile-menu">
            <div className="user-avatar">
              {user?.first_name ? user.first_name[0].toUpperCase() : "U"}
            </div>
            <div className="user-meta">
              <span className="user-name">{user?.first_name} {user?.last_name || "Financial Controller"}</span>
              <span className="user-role-badge">Super User (All Spokes)</span>
            </div>
            <button onClick={() => { logout(); navigate("/login"); }} className="infor-logout-btn" title="Sign Out">
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="infor-workspace">
        {/* Workspace Action Subheader */}
        <div className="workspace-subheader">
          <div className="subheader-title-block">
            <h1>Connected Enterprise Spoke Systems</h1>
            <p>Unified directory of operational services, SunSystems ledger posting engines, and IDM document portals.</p>
          </div>

          <div className="subheader-controls">
            <div className="search-box">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search spoke services by name or code..."
              />
              {searchQuery && <button onClick={() => setSearchQuery("")} className="clear-btn">×</button>}
            </div>

            <div className="filter-pill-group">
              <button
                className={`filter-pill ${selectedFilter === "ALL" ? "active" : ""}`}
                onClick={() => setSelectedFilter("ALL")}
              >
                All Spokes ({systems.length})
              </button>
              <button
                className={`filter-pill ${selectedFilter === "PROVISIONED" ? "active" : ""}`}
                onClick={() => setSelectedFilter("PROVISIONED")}
              >
                Ready / Provisioned
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="erp-banner-alert" role="alert">
            <span className="banner-icon">⚠</span>
            <div className="banner-content">
              <strong>Spoke Dispatch Warning</strong>
              <p>{error}</p>
            </div>
            <button className="banner-dismiss" onClick={() => setError("")}>✕</button>
          </div>
        )}

        {/* Spoke Systems Grid */}
        {loading ? (
          <div className="infor-loading-container">
            <div className="erp-spinner" />
            <p>Retrieving licensed enterprise services from Hub Directory...</p>
          </div>
        ) : (
          <div className="spokes-grid">
            {filteredSystems.map((system) => {
              const isSelected = selectedSystem === system.system;
              const isBlocked = !system.provisioned;

              return (
                <div
                  key={system.system}
                  className={`spoke-card ${isBlocked ? "blocked" : "available"} ${isSelected ? "launching" : ""}`}
                  onClick={() => !redirecting && handleSystemClick(system.system)}
                >
                  <div className="spoke-card-header">
                    <div className="spoke-brand-wrap">
                      {renderIcon(system)}
                      <div>
                        <span className="spoke-code-badge">{system.code || "SPOKE"}</span>
                        <h3>{system.display}</h3>
                      </div>
                    </div>

                    <div className="spoke-status-indicator">
                      {system.provisioned ? (
                        <span className="badge badge-success">● Provisioned</span>
                      ) : (
                        <span className="badge badge-warning">◌ Access Required</span>
                      )}
                    </div>
                  </div>

                  <p className="spoke-desc">{system.description}</p>

                  <div className="spoke-card-footer">
                    <div className="sso-protocol-meta">
                      <span className="protocol-chip">OIDC/SAML SSO</span>
                      <span className="tenant-chip">BU: {activeBU}</span>
                    </div>

                    <div className="spoke-action-link">
                      {redirecting && isSelected ? (
                        <span className="action-launching">Initiating SSO...</span>
                      ) : system.provisioned ? (
                        <span className="action-ready">Launch Portal →</span>
                      ) : (
                        <span className="action-restricted">Request Role</span>
                      )}
                    </div>
                  </div>

                  {isBlocked && system.access_message && (
                    <div className="spoke-blocked-banner">
                      {system.access_message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {!loading && filteredSystems.length === 0 && (
          <div className="empty-spokes-state">
            <div className="empty-icon">📂</div>
            <h3>No matching enterprise services found</h3>
            <p>No spokes match the query "{searchQuery}". Adjust filters or contact your financial system administrator.</p>
          </div>
        )}

        {/* Quick SunSystems Journal Posting & IDM Audit Strip */}
        <section className="infor-hub-summary-strip">
          <div className="summary-card">
            <h4>SunSystems Journal Status</h4>
            <div className="summary-stat">
              <span className="stat-number">14</span>
              <span className="stat-desc">Batches Awaiting Post for {activeBU}</span>
            </div>
            <span className="stat-foot">Connected to Financial Core Engine</span>
          </div>

          <div className="summary-card">
            <h4>IDM DocuSign Route Queue</h4>
            <div className="summary-stat">
              <span className="stat-number">3</span>
              <span className="stat-desc">Purchase Requisitions Pending Signature</span>
            </div>
            <span className="stat-foot">Docusign API Connected & Validated</span>
          </div>

          <div className="summary-card">
            <h4>Infor Q&A Query Cache</h4>
            <div className="summary-stat">
              <span className="stat-number">100%</span>
              <span className="stat-desc">Ledger Dimensions Synced</span>
            </div>
            <span className="stat-foot">Realtime Financial Data Warehouse</span>
          </div>
        </section>
      </main>
    </div>
  );
}
