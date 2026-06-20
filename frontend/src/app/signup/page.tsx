"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Loader2 } from "lucide-react";

export default function SignupPage() {
  const [error, setError] = useState("");
  const [googleLoading, setGoogleLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [emailLoading, setEmailLoading] = useState(false);
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  const handleGoogleSignup = async () => {
    setError("");
    setGoogleLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      setError(error.message);
      setGoogleLoading(false);
    }
  };

  const handleMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    setError("");
    setEmailLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email: trimmed,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    setEmailLoading(false);
    if (error) {
      setError(error.message);
    } else {
      setMagicLinkSent(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2.5">
            <div className="flex items-center justify-center text-white font-extrabold" style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)", fontSize: 15 }}>F</div>
            <span className="font-extrabold" style={{ fontSize: 20, color: "#1B4D3E", letterSpacing: -0.5 }}>
              File<span style={{ color: "#E8B931" }}>BRSR</span>
            </span>
          </Link>
          <h1 className="mt-6 text-2xl font-bold text-foreground">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-muted">
            Start with 3 free BRSR report extractions
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-border p-8">
          {error && (
            <div className="p-3 mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
              {error}
            </div>
          )}

          {magicLinkSent ? (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-center">
              <p className="text-sm font-semibold text-emerald-800">Check your inbox</p>
              <p className="mt-1 text-xs text-emerald-700/80">
                We sent a sign-in link to <span className="font-medium">{email.trim()}</span>. Open it on this
                device to finish creating your account.
              </p>
              <button
                type="button"
                onClick={() => setMagicLinkSent(false)}
                className="mt-3 text-xs font-medium text-emerald-700 hover:underline"
              >
                Use a different email
              </button>
            </div>
          ) : (
            <>
              <button
                type="button"
                onClick={handleGoogleSignup}
                disabled={googleLoading}
                className="w-full flex items-center justify-center gap-3 py-3 border border-border rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 font-medium text-sm"
              >
                {googleLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                )}
                Sign up with Google
              </button>

              <div className="flex items-center gap-3 my-5">
                <div className="h-px flex-1 bg-gray-200" />
                <span className="text-xs text-gray-400">or</span>
                <div className="h-px flex-1 bg-gray-200" />
              </div>

              <form onSubmit={handleMagicLink} className="space-y-3">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                  className="w-full px-4 py-3 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                />
                <button
                  type="submit"
                  disabled={emailLoading || !email.trim()}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium text-sm text-white disabled:opacity-50"
                  style={{ background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)" }}
                >
                  {emailLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Email me a magic link
                </button>
              </form>
            </>
          )}

          <p className="mt-4 text-center text-xs text-muted">
            By signing up, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>

        <p className="mt-6 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-primary font-medium hover:underline"
            style={{ color: "#1B4D3E" }}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
