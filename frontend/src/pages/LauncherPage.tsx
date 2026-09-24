import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { launcherAPI } from "../services/api";

type AccessStatus = "ready" | "not_provisioned" | "unavailable";

interface LicensedSystem {
  system: string;
  display: string;
  description?: string;
  info_url?: string;
  public_url?: string;
  licensed: boolean;
  expires_at?: string | null;
  status?: AccessStatus;
  provisioned?: boolean;
  access_message?: string | null;
}

const STATUS_CONFIG: Record<
  AccessStatus,
  { label: string; badgeClass: string; dotClass: string }
> = {
  ready: {
    label: "Ready to open",
    badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dotClass: "bg-emerald-500",
  },
  not_provisioned: {
    label: "Account not set up",
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
    dotClass: "bg-amber-500",
  },
  unavailable: {
    label: "Unavailable",
    badgeClass: "bg-slate-100 text-slate-600 border-slate-200",
    dotClass: "bg-slate-400",
  },
};

function getSystemStatus(system: LicensedSystem): AccessStatus {
  if (system.status) return system.status;
  if (system.provisioned) return "ready";
  if (system.licensed) return "not_provisioned";
  return "unavailable";
}

function getInitials(name: string): string {
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
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  useEffect(() => {
    const fetchSystems = async () => {
      try {
        const { data } = await launcherAPI.getLicensedSystems();
        setSystems(data.systems || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load licensed systems");
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
    const status = getSystemStatus(system);
    if (redirecting || status !== "ready") return;

    setSelectedSystem(system.system);
    setRedirecting(true);
    setError("");

    try {
      const { data } = await launcherAPI.initiateSSO(system.system);
      if (!data.redirect_url) {
        setError(data.access_message || "SSO launch authorization was denied");
        setRedirecting(false);
        setSelectedSystem(null);
        return;
      }
      window.location.href = data.redirect_url;
    } catch (err: any) {
      setError(
        err.response?.data?.access_message ||
          err.response?.data?.detail ||
          "Failed to initiate SSO with the selected system"
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
      const status = getSystemStatus(system);
      const matchesFilter = selectedFilter === "ALL" || status === selectedFilter;
      const matchesQuery =
        !query ||
        `${system.display} ${system.description || ""}`.toLowerCase().includes(query);
      return matchesFilter && matchesQuery;
    });
  }, [searchQuery, selectedFilter, systems]);

  const readyCount = useMemo(
    () => systems.filter((s) => getSystemStatus(s) === "ready").length,
    [systems]
  );
  const attentionCount = useMemo(
    () => systems.filter((s) => getSystemStatus(s) !== "ready").length,
    [systems]
  );

  return (
    <div className="min-h-screen bg-[#f4f7fa] flex flex-col text-[#1c2a3a]">
      {/* ── Top Command Bar ────────────────────────────────────────────── */}
      <header className="bg-[#182332] text-white border-b-[3px] border-[#c71f37] h-14 flex items-center justify-between px-4 sm:px-6 shadow-sm z-30 flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setSidebarOpen((prev) => !prev)}
            className="p-1.5 rounded text-slate-300 hover:text-white hover:bg-[#202d3f] transition-colors focus:outline-none focus:ring-2 focus:ring-[#c71f37]"
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            aria-label="Toggle navigation sidebar"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 rounded bg-[#c71f37] text-white flex items-center justify-center font-bold text-sm shadow-sm">
              F
            </span>
            <div className="leading-tight">
              <span className="text-[10px] font-bold tracking-wider text-rose-300 uppercase block">
                FLAXEM PLATFORM
              </span>
              <h1 className="text-sm font-semibold text-white tracking-wide">
                Financial Systems Hub
              </h1>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#2c3c52] border border-slate-600 flex items-center justify-center text-xs font-semibold text-slate-200">
              {user?.first_name ? user.first_name[0].toUpperCase() : "U"}
            </div>
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-xs font-medium text-white leading-tight">
                {user?.first_name} {user?.last_name || "User"}
              </span>
              <span className="text-[11px] text-slate-400">Authenticated Session</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="text-xs text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 hover:bg-[#202d3f] px-3 py-1.5 rounded transition-all"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Main Layout Body (Sidebar + Content Canvas) ─────────────────── */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* ── Left Navigation Sidebar ───────────────────────────────────── */}
        <aside
          className={`bg-white border-r border-[#d4dce5] transition-all duration-300 ease-in-out flex flex-col flex-shrink-0 z-20 ${
            sidebarOpen ? "w-72" : "w-0 -translate-x-full lg:w-16 lg:translate-x-0"
          }`}
        >
          {sidebarOpen ? (
            <div className="flex flex-col h-full w-72">
              <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    SYSTEMS DIRECTORY
                  </span>
                  <p className="text-xs font-semibold text-slate-800">
                    Connected Spokes ({systems.length})
                  </p>
                </div>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="text-slate-400 hover:text-slate-700 text-xs p-1 rounded"
                  title="Close sidebar"
                >
                  ✕
                </button>
              </div>

              {/* Navigation List */}
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {systems.map((system) => {
                  const status = getSystemStatus(system);
                  const isReady = status === "ready";
                  const isSelected = selectedSystem === system.system;

                  return (
                    <button
                      key={system.system}
                      type="button"
                      disabled={!isReady || redirecting}
                      onClick={() => handleSystemClick(system)}
                      className={`w-full text-left px-3 py-2.5 rounded-md flex items-center gap-3 transition-colors ${
                        isSelected
                          ? "bg-rose-50 border border-[#c71f37] text-[#182332]"
                          : isReady
                          ? "hover:bg-slate-50 text-slate-700"
                          : "opacity-60 cursor-not-allowed bg-slate-50/50 text-slate-400"
                      }`}
                    >
                      <div
                        className={`w-8 h-8 rounded flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                          isReady ? "bg-slate-100 text-slate-700" : "bg-slate-200 text-slate-400"
                        }`}
                      >
                        {getInitials(system.display)}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold truncate block text-slate-900">
                            {system.display}
                          </span>
                          <span
                            className={`w-2 h-2 rounded-full flex-shrink-0 ${
                              STATUS_CONFIG[status].dotClass
                            }`}
                          />
                        </div>
                        <span className="text-[11px] text-slate-500 block truncate">
                          {STATUS_CONFIG[status].label}
                        </span>
                      </div>
                    </button>
                  );
                })}

                {systems.length === 0 && !loading && (
                  <div className="text-xs text-slate-400 p-4 text-center">
                    No licensed systems found.
                  </div>
                )}
              </div>

              {/* Sidebar Quick Footer */}
              <div className="p-3 border-t border-slate-200 bg-slate-50/70 text-[11px] text-slate-500 flex justify-between items-center">
                <span>Provisioned: <strong>{readyCount}</strong></span>
                <span>Restricted: <strong>{attentionCount}</strong></span>
              </div>
            </div>
          ) : (
            /* Collapsed mini-bar */
            <div className="hidden lg:flex flex-col items-center py-4 space-y-3 w-16">
              {systems.map((system) => {
                const status = getSystemStatus(system);
                return (
                  <button
                    key={system.system}
                    onClick={() => handleSystemClick(system)}
                    title={`${system.display} (${STATUS_CONFIG[status].label})`}
                    className="w-10 h-10 rounded bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-700 relative transition-colors"
                  >
                    {getInitials(system.display)}
                    <span
                      className={`absolute bottom-1 right-1 w-2 h-2 rounded-full ${
                        STATUS_CONFIG[status].dotClass
                      }`}
                    />
                  </button>
                );
              })}
            </div>
          )}
        </aside>

        {/* ── Main Workspace Canvas ────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-8">
          <div className="max-w-6xl mx-auto space-y-6">
            {/* Header intro & metrics */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-[#d4dce5]">
              <div>
                <span className="text-[11px] font-bold text-[#c71f37] tracking-wider uppercase">
                  ENTERPRISE HUBS &amp; SPOKES
                </span>
                <h2 className="text-2xl font-bold text-[#182332] tracking-tight">
                  Licensed Services Directory
                </h2>
                <p className="text-sm text-slate-600 mt-0.5">
                  Launch provisioned systems or verify authorization status across enterprise spokes.
                </p>
              </div>

              {/* Status KPI Tiles */}
              <div className="grid grid-cols-3 gap-2 text-center flex-shrink-0">
                <div className="bg-white border border-[#d4dce5] rounded px-3 py-2">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase block">Total</span>
                  <strong className="text-base font-bold text-[#182332]">{systems.length}</strong>
                </div>
                <div className="bg-white border border-[#d4dce5] rounded px-3 py-2">
                  <span className="text-[10px] font-semibold text-emerald-700 uppercase block">Ready</span>
                  <strong className="text-base font-bold text-emerald-600">{readyCount}</strong>
                </div>
                <div className="bg-white border border-[#d4dce5] rounded px-3 py-2">
                  <span className="text-[10px] font-semibold text-amber-800 uppercase block">Attention</span>
                  <strong className="text-base font-bold text-amber-600">{attentionCount}</strong>
                </div>
              </div>
            </div>

            {/* Error Notification */}
            {error && (
              <div
                className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-md text-sm flex items-start justify-between gap-3 shadow-sm"
                role="alert"
              >
                <div className="flex items-center gap-2">
                  <span className="text-base">⚠</span>
                  <span>{error}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setError("")}
                  className="text-red-500 hover:text-red-700 font-bold"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Filter & Search Toolbar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <div className="relative flex-1 max-w-md">
                <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 text-sm">
                  🔍
                </span>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search systems by name or keywords..."
                  className="w-full pl-9 pr-8 py-2 text-sm bg-white border border-[#d4dce5] rounded-md focus:outline-none focus:ring-2 focus:ring-[#c71f37] focus:border-transparent text-slate-900 shadow-sm"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-600"
                  >
                    ✕
                  </button>
                )}
              </div>

              <div className="flex items-center gap-1 bg-slate-200/80 p-1 rounded-md self-start sm:self-auto overflow-x-auto max-w-full">
                {(["ALL", "ready", "not_provisioned", "unavailable"] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setSelectedFilter(filter)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded whitespace-nowrap transition-all ${
                      selectedFilter === filter
                        ? "bg-white text-[#182332] shadow-sm"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {filter === "ALL" ? "All Systems" : STATUS_CONFIG[filter].label}
                  </button>
                ))}
              </div>
            </div>

            {/* Systems Grid */}
            {loading ? (
              <div className="text-center py-20 bg-white border border-[#d4dce5] rounded-lg">
                <div className="w-8 h-8 border-2 border-slate-300 border-t-[#c71f37] rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-slate-500 font-medium">
                  Loading licensed services directory...
                </p>
              </div>
            ) : filteredSystems.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredSystems.map((system) => {
                  const status = getSystemStatus(system);
                  const isReady = status === "ready";
                  const isSelected = selectedSystem === system.system;

                  return (
                    <div
                      key={system.system}
                      onClick={() => handleSystemClick(system)}
                      className={`group relative bg-white border rounded-lg p-5 flex flex-col justify-between transition-all shadow-sm ${
                        isReady
                          ? "cursor-pointer hover:border-[#c71f37] hover:shadow-md hover:-translate-y-0.5 border-[#d4dce5]"
                          : "border-slate-200 bg-slate-50/60 opacity-80 cursor-not-allowed border-dashed"
                      } ${isSelected ? "ring-2 ring-[#c71f37] border-transparent" : ""}`}
                    >
                      {/* Topline indicator */}
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-md bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-sm text-[#182332] group-hover:bg-rose-50 group-hover:border-rose-200 group-hover:text-[#c71f37] transition-colors">
                              {getInitials(system.display)}
                            </div>
                            <div>
                              <h3 className="text-base font-bold text-[#182332] group-hover:text-[#c71f37] transition-colors leading-snug">
                                {system.display}
                              </h3>
                            </div>
                          </div>

                          <span
                            className={`text-[11px] font-semibold px-2 py-0.5 rounded border inline-flex items-center gap-1.5 whitespace-nowrap ${
                              STATUS_CONFIG[status].badgeClass
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_CONFIG[status].dotClass}`} />
                            {STATUS_CONFIG[status].label}
                          </span>
                        </div>

                        {system.description && (
                          <p className="text-xs text-slate-600 line-clamp-2 mb-4 leading-relaxed">
                            {system.description}
                          </p>
                        )}
                      </div>

                      {/* Card Footer & Launch Actions */}
                      <div className="pt-3 border-t border-slate-100 mt-2 flex flex-col gap-2">
                        <div className="flex items-center justify-between text-xs">
                          {isReady ? (
                            <span className="font-semibold text-[#c71f37] group-hover:underline inline-flex items-center gap-1">
                              {redirecting && isSelected ? "Connecting SSO..." : "Open System →"}
                            </span>
                          ) : (
                            <span className="text-slate-400 font-medium">Access Restricted</span>
                          )}

                          {system.expires_at && (
                            <span className="text-[11px] text-slate-400">
                              Expires {new Date(system.expires_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>

                        {!isReady && system.access_message && (
                          <div className="text-[11px] text-amber-800 bg-amber-50/80 border border-amber-200/80 p-2 rounded">
                            {system.access_message}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-16 bg-white border border-[#d4dce5] rounded-lg">
                <span className="text-3xl block mb-2">📂</span>
                <strong className="text-sm text-slate-800 block">No products match this view</strong>
                <p className="text-xs text-slate-500 mt-1">
                  Try adjusting your search terms or filter selection.
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
