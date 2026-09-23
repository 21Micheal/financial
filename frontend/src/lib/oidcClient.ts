import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const KEYCLOAK_URL =
  import.meta.env.VITE_OIDC_AUTHORITY ?? "http://localhost:8080/realms/idp-dev";
const CLIENT_ID = import.meta.env.VITE_OIDC_CLIENT_ID ?? "financial-client";

export const oidcManager = new UserManager({
  authority: KEYCLOAK_URL,
  client_id: CLIENT_ID,
  redirect_uri: `${window.location.origin}/auth/callback`,
  silent_redirect_uri: `${window.location.origin}/auth/silent-renew.html`,
  post_logout_redirect_uri: window.location.origin,
  response_type: "code",
  scope: "openid profile email",
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
});

export async function oidcLogin(): Promise<void> {
  await oidcManager.signinRedirect();
}

export async function handleOidcCallback() {
  return await oidcManager.signinRedirectCallback();
}

export async function trySilentRenew() {
  try {
    return await oidcManager.signinSilent();
  } catch {
    return null;
  }
}

export async function oidcLogout(): Promise<void> {
  try {
    await oidcManager.signoutRedirect();
  } catch {
    try {
      await oidcManager.removeUser();
    } catch {
      sessionStorage.clear();
    }
  }
}
