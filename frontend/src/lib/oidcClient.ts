/**
 * oidcClient.ts — Financial System
 *
 * monitorSession fix: the UserSignedOut handler now:
 *   1. Guards against acting when already logged out (breaks the /login loop).
 *   2. Calls oidcManager.removeUser() to erase the stale OIDC user from
 *      localStorage before redirecting — this stops the session monitor from
 *      detecting "no KC session" on the next page load and looping again.
 *
 * oidcLogout() also calls removeUser() before signoutRedirect() for the same
 * reason: once we've decided to log out, we clear the monitor's tracking data
 * so no UserSignedOut can fire during or after the Keycloak redirect.
 */
import { UserManager, WebStorageStateStore } from 'oidc-client-ts'
import { useAuthStore } from '../store/authStore'

const KEYCLOAK_URL =
  import.meta.env.VITE_OIDC_AUTHORITY ?? 'http://localhost:8080/realms/idp-dev'
const CLIENT_ID = import.meta.env.VITE_OIDC_CLIENT_ID ?? 'financial-client'

export const oidcManager = new UserManager({
  authority:                KEYCLOAK_URL,
  client_id:                CLIENT_ID,
  redirect_uri:             `${window.location.origin}/auth/callback`,
  silent_redirect_uri:      `${window.location.origin}/auth/silent-renew.html`,
  post_logout_redirect_uri: `${window.location.origin}/login`,
  response_type:            'code',
  scope:                    'openid profile email',
  // localStorage keeps OIDC state shared across tabs
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  // Poll the Keycloak check_session iframe to detect remote logouts
  monitorSession: true,
})

// Fired when the Keycloak session ends from any registered client.
oidcManager.events.addUserSignedOut(async () => {
  const { isAuthenticated, logout } = useAuthStore.getState()

  // GUARD: only act when we have a live local session.
  // Without this, every page load after logout re-fires UserSignedOut
  // (stale session_state still in localStorage) → infinite /login loop.
  if (!isAuthenticated) return

  // Remove the OIDC user from localStorage NOW so the monitor has no
  // session_state to track on subsequent page loads (stops the loop source).
  try { await oidcManager.removeUser() } catch { /* ignore */ }

  logout()
  window.location.replace('/login')
})

export async function oidcLogin(idpHint?: string): Promise<void> {
  await oidcManager.signinRedirect(
    idpHint ? { extraQueryParams: { kc_idp_hint: idpHint } } : {}
  )
}

export async function handleOidcCallback() {
  return await oidcManager.signinRedirectCallback()
}

export async function trySilentRenew() {
  try {
    return await oidcManager.signinSilent()
  } catch {
    return null
  }
}

/**
 * End the Keycloak session.
 *
 * MUST be called LAST in the logout sequence (it redirects the browser).
 * Caller must blacklist the refresh token and clear Zustand state first.
 *
 * removeUser() is called before signoutRedirect() to clear the OIDC user
 * (including session_state) from localStorage. This prevents the session
 * monitor from firing UserSignedOut on /login after the redirect completes.
 */
export async function oidcLogout(idToken?: string | null): Promise<void> {
  try {
    // Remove the stored OIDC user BEFORE redirecting so the monitor cannot
    // fire a spurious UserSignedOut on the /login landing page.
    try { await oidcManager.removeUser() } catch { /* ignore */ }
    await oidcManager.signoutRedirect({
      id_token_hint: idToken ?? undefined,
      post_logout_redirect_uri: `${window.location.origin}/login`,
    })
  } catch {
    try { await oidcManager.removeUser() } catch { /* ignore */ }
    window.location.replace('/login')
  }
}
