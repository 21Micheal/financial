import { useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, LogOut, User as UserIcon } from "../ui/icons";
import { clsx } from "../ui/clsx";
import { useAuthStore } from "../../store/authStore";
import { oidcLogout } from "../../lib/oidcClient";
import { authAPI } from "../../services/api";

interface LayoutProps {
  children: ReactNode;
  sidebar?: (collapsed: boolean) => ReactNode;
  sidebarTitle?: string;
  sidebarSubtitle?: string;
  sidebarFooter?: (collapsed: boolean) => ReactNode;
}

export function Layout({
  children,
  sidebar,
  sidebarTitle = "SYSTEMS DIRECTORY",
  sidebarSubtitle,
  sidebarFooter,
}: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { user, logout, idToken, refreshToken } = useAuthStore();

  const handleLogout = async () => {
    if (refreshToken) {
      try {
        await authAPI.logout(refreshToken);
      } catch {
        /* ignore */
      }
    }
    logout();
    await oidcLogout(idToken);
  };

  const toggleSidebar = () => setSidebarCollapsed((prev) => !prev);

  return (
    <div className="flex h-screen flex-col bg-[#EDEDED] text-[#1F2933]">
      {/* ── Single continuous blue command bar (full-width, no sidebar indent) */}
      <header className="flex h-14 shrink-0 items-center bg-[#287EAD] text-white shadow-sm z-30">
        {/* Portal mount — WorkspaceCommandBar from each page renders here */}
        <div id="wcb-slot" className="flex min-w-0 flex-1 items-center" />

        {/* Global actions: User Profile & Sign out */}
        <div className="flex shrink-0 items-center gap-3 border-l border-white/20 pl-4 pr-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-white/30 bg-white/15 text-xs font-semibold text-white shadow-inner">
              {user?.first_name ? user.first_name[0].toUpperCase() : <UserIcon className="h-4 w-4" />}
            </div>
            <div className="hidden flex-col text-right sm:flex">
              <span className="text-xs font-medium leading-tight text-white">
                {user?.first_name ? `${user.first_name} ${user.last_name || ""}` : "Authenticated User"}
              </span>
              <span className="text-[10px] text-white/70">Authenticated Session</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center gap-1.5 border border-white/20 bg-white/10 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-white/20 hover:text-white"
            title="Sign out of financial systems"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </header>

      {/* ── Body Row: Sidebar on Left, Content Canvas on Right ── */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* ── Sidebar ── */}
        <aside
          className={clsx(
            "flex flex-shrink-0 flex-col overflow-hidden border-r border-[#C8CDD2] bg-[#F6F7F8] text-[#1F2933] transition-[width] duration-200 z-20",
            sidebarCollapsed ? "w-[52px]" : "w-[260px]",
          )}
        >
          {/* Sidebar header (clean, toggle button, NO logo as requested) */}
          <div
            className={clsx(
              "flex h-14 shrink-0 items-center border-b border-[#C8CDD2] bg-[#F6F7F8]",
              sidebarCollapsed ? "justify-center px-0" : "justify-between px-3",
            )}
          >
            {!sidebarCollapsed && (
              <div className="min-w-0 pr-2">
                <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  {sidebarTitle}
                </span>
                {sidebarSubtitle && (
                  <p className="truncate text-xs font-semibold text-slate-800">
                    {sidebarSubtitle}
                  </p>
                )}
              </div>
            )}
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex h-8 w-8 shrink-0 items-center justify-center text-[#6E767D] transition-colors hover:bg-[#E8EAEC] hover:text-[#1F2933]"
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-expanded={!sidebarCollapsed}
            >
              {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>

          {/* Sidebar content */}
          <div className="scrollbar-minimal flex-1 overflow-y-auto">
            {sidebar ? sidebar(sidebarCollapsed) : null}
          </div>

          {/* Sidebar footer */}
          {sidebarFooter && (
            <div className="border-t border-[#C8CDD2] bg-[#F6F7F8]">
              {sidebarFooter(sidebarCollapsed)}
            </div>
          )}
        </aside>

        {/* ── Main Content Canvas (distinguishable off-white #EDEDED) ── */}
        <main className="flex-1 overflow-y-auto bg-[#EDEDED] p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
