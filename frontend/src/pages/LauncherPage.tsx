import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Search, X, AlertTriangle, Layers } from "../components/ui/icons";
import { clsx } from "../components/ui/clsx";
import { useAuthStore } from "../store/authStore";
import { launcherAPI } from "../services/api";
import { Layout } from "../components/shared/Layout";
import { WorkspaceCommandBar } from "../components/shared/WorkspaceCommandBar";

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

  const navigate = useNavigate();
  const { logout } = useAuthStore();

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
    <Layout
      sidebarTitle="SYSTEMS DIRECTORY"
      sidebarSubtitle={`Connected Spokes (${systems.length})`}
      sidebar={(collapsed) => (
        <div className="py-2">
          {collapsed ? (
            /* Collapsed mini-bar: squared icon buttons with status dot */
            <div className="flex flex-col items-center space-y-2 px-1 py-1">
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
                    title={`${system.display} (${STATUS_CONFIG[status].label})`}
                    className={clsx(
                      "relative flex h-9 w-9 items-center justify-center text-xs font-bold transition-colors",
                      isSelected
                        ? "bg-[#C5E6F5] text-[#0B3B60] border border-[#287EAD] font-semibold shadow"
                        : isReady
                        ? "border border-[#C8CDD2] bg-white text-[#182332] hover:bg-[#EEF3F7]"
                        : "cursor-not-allowed border border-[#D7DCE0] bg-[#E8EAEC] text-slate-400 opacity-60"
                    )}
                  >
                    {getInitials(system.display)}
                    <span
                      className={clsx(
                        "absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border border-white",
                        STATUS_CONFIG[status].dotClass
                      )}
                    />
                  </button>
                );
              })}
            </div>
          ) : (
            /* Expanded nav: neatly arranged, left-aligned, squared active item */
            <div className="space-y-1 px-2">
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
                    className={clsx(
                      "flex w-full items-center gap-2.5 px-2.5 py-2 text-left transition-colors",
                      isSelected
                        ? "border-l-4 border-[#287EAD] bg-[#C5E6F5] text-[#0B3B60] font-semibold"
                        : isReady
                        ? "border-l-4 border-transparent text-[#1F2933] hover:bg-[#E8EAEC]"
                        : "border-l-4 border-transparent text-slate-400 opacity-60 cursor-not-allowed"
                    )}
                  >
                    <div
                      className={clsx(
                        "flex h-7 w-7 shrink-0 items-center justify-center text-xs font-bold",
                        isSelected
                          ? "bg-white/20 text-white"
                          : isReady
                          ? "border border-[#C8CDD2] bg-white text-[#182332]"
                          : "bg-slate-200 text-slate-400"
                      )}
                    >
                      {getInitials(system.display)}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span
                          className={clsx(
                            "truncate text-xs font-semibold",
                            isSelected ? "text-[#0B3B60] font-bold" : "text-[#1F2933]"
                          )}
                        >
                          {system.display}
                        </span>
                        <span
                          className={clsx(
                            "h-1.5 w-1.5 shrink-0 rounded-full",
                            STATUS_CONFIG[status].dotClass
                          )}
                        />
                      </div>
                      <span
                        className={clsx(
                          "block truncate text-[10px]",
                          isSelected ? "text-[#0B3B60]/80" : "text-slate-500"
                        )}
                      >
                        {STATUS_CONFIG[status].label}
                      </span>
                    </div>
                  </button>
                );
              })}

              {systems.length === 0 && !loading && (
                <div className="p-4 text-center text-xs text-slate-400">
                  No licensed systems found.
                </div>
              )}
            </div>
          )}
        </div>
      )}
      sidebarFooter={(collapsed) => (
        collapsed ? (
          <div className="py-2 text-center text-[10px] font-bold text-slate-500">
            {readyCount}/{systems.length}
          </div>
        ) : (
          <div className="flex items-center justify-between p-3 text-[11px] text-slate-600">
            <span>
              Provisioned: <strong>{readyCount}</strong>
            </span>
            <span>
              Restricted: <strong>{attentionCount}</strong>
            </span>
          </div>
        )
      )}
    >
      {/* ── Top Blue Command Bar Content ───────────────────────────────── */}
      <WorkspaceCommandBar
        actions={
          <div className="flex items-center gap-2 text-xs text-white/90">
            <span className="hidden md:inline text-white/80">Active Spokes:</span>
            <span className="bg-white/20 px-2 py-0.5 font-semibold text-white">
              {readyCount} of {systems.length}
            </span>
          </div>
        }
      >
        <div className="flex items-center gap-2 text-white">
          <Layers className="h-4 w-4 text-white/80" />
          <span className="text-xs font-semibold uppercase tracking-wider text-white/80">
            Operations Workspace
          </span>
          <span className="text-white/40">/</span>
          <span className="text-sm font-semibold tracking-wide text-white">
            Financial Systems Hub
          </span>
        </div>
      </WorkspaceCommandBar>

      {/* ── Main Canvas (Matching DashboardPage & Designer Canvas) ──────── */}
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Operations Heading & Summary Tiles */}
        <div className="flex flex-col justify-between gap-4 border-b border-[#C8CDD2] pb-5 md:flex-row md:items-end">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#287EAD]">
              ENTERPRISE HUBS &amp; SPOKES
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-[#182332]">
              Licensed Services Directory
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Launch provisioned systems or verify authorization status across enterprise spokes.
            </p>
          </div>

          {/* Status KPI Tiles */}
          <div className="grid grid-cols-3 gap-2 text-center shrink-0">
            <div className="border border-[#C8CDD2] bg-white px-3.5 py-2 shadow-sm">
              <span className="block text-[10px] font-semibold uppercase text-slate-500">
                Total
              </span>
              <strong className="text-base font-bold text-[#182332]">
                {systems.length}
              </strong>
            </div>
            <div className="border border-emerald-200 bg-white px-3.5 py-2 shadow-sm">
              <span className="block text-[10px] font-semibold uppercase text-emerald-700">
                Ready
              </span>
              <strong className="text-base font-bold text-emerald-600">
                {readyCount}
              </strong>
            </div>
            <div className="border border-amber-200 bg-white px-3.5 py-2 shadow-sm">
              <span className="block text-[10px] font-semibold uppercase text-amber-800">
                Attention
              </span>
              <strong className="text-base font-bold text-amber-600">
                {attentionCount}
              </strong>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            className="flex items-start justify-between gap-3 border border-red-200 bg-red-50 p-3.5 text-sm text-red-800 shadow-sm"
            role="alert"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => setError("")}
              className="text-red-500 hover:text-red-700"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Filter & Search Toolbar */}
        <div className="flex flex-col items-stretch justify-between gap-3 sm:flex-row sm:items-center">
          <div className="relative max-w-md flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search systems by name or keywords..."
              className="w-full border border-[#C8CDD2] bg-white py-2 pl-9 pr-8 text-sm text-slate-900 shadow-sm focus:border-[#287EAD] focus:outline-none focus:ring-1 focus:ring-[#287EAD]"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-1 overflow-x-auto border border-[#C8CDD2] bg-white p-1 shadow-sm">
            {(["ALL", "ready", "not_provisioned", "unavailable"] as const).map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => setSelectedFilter(filter)}
                className={clsx(
                  "px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-colors",
                  selectedFilter === filter
                    ? "bg-[#C5E6F5] text-[#0B3B60] border border-[#287EAD] font-semibold shadow-sm"
                    : "text-slate-600 hover:bg-[#EEF3F7] hover:text-slate-900"
                )}
              >
                {filter === "ALL" ? "All Systems" : STATUS_CONFIG[filter].label}
              </button>
            ))}
          </div>
        </div>

        {/* Systems Grid */}
        {loading ? (
          <div className="border border-[#C8CDD2] bg-white py-20 text-center shadow-sm">
            <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-[#287EAD]" />
            <p className="text-sm font-medium text-slate-500">
              Loading licensed services directory...
            </p>
          </div>
        ) : filteredSystems.length > 0 ? (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {filteredSystems.map((system) => {
              const status = getSystemStatus(system);
              const isReady = status === "ready";
              const isSelected = selectedSystem === system.system;

              return (
                <div
                  key={system.system}
                  onClick={() => handleSystemClick(system)}
                  className={clsx(
                    "group relative flex flex-col justify-between border bg-white p-5 shadow-sm transition-all",
                    isReady
                      ? "cursor-pointer border-[#C8CDD2] hover:-translate-y-0.5 hover:border-[#287EAD] hover:shadow-md"
                      : "cursor-not-allowed border-dashed border-slate-200 bg-slate-50/70 opacity-80",
                    isSelected && "ring-2 ring-[#287EAD] border-transparent"
                  )}
                >
                  <div>
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center border border-[#C8CDD2] bg-[#F6F7F8] font-bold text-sm text-[#182332] transition-colors group-hover:border-[#287EAD] group-hover:bg-[#EEF3F7] group-hover:text-[#287EAD]">
                          {getInitials(system.display)}
                        </div>
                        <div>
                          <h3 className="text-base font-bold text-[#182332] transition-colors group-hover:text-[#287EAD] leading-snug">
                            {system.display}
                          </h3>
                        </div>
                      </div>

                      <span
                        className={clsx(
                          "inline-flex items-center gap-1.5 whitespace-nowrap border px-2 py-0.5 text-[11px] font-semibold",
                          STATUS_CONFIG[status].badgeClass
                        )}
                      >
                        <span
                          className={clsx(
                            "h-1.5 w-1.5 rounded-full",
                            STATUS_CONFIG[status].dotClass
                          )}
                        />
                        {STATUS_CONFIG[status].label}
                      </span>
                    </div>

                    {system.description && (
                      <p className="mb-4 text-xs leading-relaxed text-slate-600 line-clamp-2">
                        {system.description}
                      </p>
                    )}
                  </div>

                  {/* Card Footer & Launch Actions */}
                  <div className="mt-2 flex flex-col gap-2 border-t border-slate-100 pt-3">
                    <div className="flex items-center justify-between text-xs">
                      {isReady ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-[#287EAD] group-hover:underline">
                          {redirecting && isSelected ? "Connecting SSO..." : "Open System →"}
                        </span>
                      ) : (
                        <span className="font-medium text-slate-400">
                          Access Restricted
                        </span>
                      )}

                      {system.expires_at && (
                        <span className="text-[11px] text-slate-400">
                          Expires {new Date(system.expires_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>

                    {!isReady && system.access_message && (
                      <div className="border border-amber-200/80 bg-amber-50/80 p-2 text-[11px] text-amber-800">
                        {system.access_message}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="border border-[#C8CDD2] bg-white py-16 text-center shadow-sm">
            <span className="mb-2 block text-3xl">📂</span>
            <strong className="block text-sm text-slate-800">
              No products match this view
            </strong>
            <p className="mt-1 text-xs text-slate-500">
              Try adjusting your search terms or filter selection.
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}
