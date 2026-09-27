"use client";

import { createClient } from "./client";

/**
 * Session helper shared by workspace/feature stores.
 *
 * Lays a small refresh + change-subscription layer over the raw Supabase
 * session so feature stores can survive access-token expiry without stranding
 * the user on a bare "Invalid token" toast.
 */

/** 401 thrown by cloud calls when the session is genuinely unusable. */
export class AuthSessionError extends Error {
  code = "session_expired";
  constructor(message = "Your session has expired. Sign in again to continue working with your org data.") {
    super(message);
    this.name = "AuthSessionError";
  }
}

/** True when a response is an authentication failure. */
export function isAuthFailure(res: Response): boolean {
  return res.status === 401;
}

/**
 * Resolve a usable access token: the live session first, then a single
 * refresh attempt, then "" (logged out). Never throws.
 */
export async function getSessionToken(): Promise<string> {
  const client = createClient();
  const { data } = await client.auth.getSession();
  const token = data.session?.access_token || "";
  if (token) return token;
  return refreshSessionToken();
}

/** Force a token refresh (used after a 401). Returns "" when the session is dead. */
export async function refreshSessionToken(): Promise<string> {
  const client = createClient();
  const { data, error } = await client.auth.refreshSession();
  if (error) return "";
  return data.session?.access_token || "";
}

type SessionCb = (signedIn: boolean) => void;

const _listeners: SessionCb[] = [];
let _subscribed = false;

function announce(signedIn: boolean) {
  for (const cb of _listeners) cb(signedIn);
}

/**
 * Subscribe to sign-in/sign-out/token changes. Returns an unsubscribe fn.
 * Backed by a single shared onAuthStateChange subscription.
 */
export function subscribeSession(cb: SessionCb): () => void {
  _listeners.push(cb);
  if (!_subscribed) {
    _subscribed = true;
    createClient().auth.onAuthStateChange((_event, session) => {
      announce(!!session);
    });
  }
  return () => {
    const idx = _listeners.indexOf(cb);
    if (idx >= 0) _listeners.splice(idx, 1);
  };
}