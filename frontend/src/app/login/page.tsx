"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Loader2 } from "lucide-react";

export default function LoginPage() {
  const [error, setError] = useState("");
  const [googleLoading, setGoogleLoading] = useState(false);

  const handleGoogleLogin = async () => {
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2.5">
            <img src="/logo-icon.svg" alt="FileBRSR" width={36} height={36} />
            <span className="font-extrabold" style={{ fontSize: 20, color: "#1B4D3E", letterSpacing: -0.5 }}>
              File<span style={{ color: "#E8B931" }}>BRSR</span>
            </span>
          </Link>
          <h1 className="mt-6 text-2xl font-bold text-foreground">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-muted">
            Sign in with your Google account to continue
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-border p-8">
          {error && (
            <div className="p-3 mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={handleGoogleLogin}
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
            Continue with Google
          </button>

          <p className="mt-4 text-center text-xs text-muted">
            By signing in, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>

        <p className="mt-6 text-center text-sm text-muted">
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="text-primary font-medium hover:underline"
            style={{ color: "#1B4D3E" }}
          >
            Sign up free
          </Link>
        </p>

        {/* Demo CTA for first-time visitors */}
        <div className="mt-8 pt-6 border-t border-gray-100">
          <p className="text-center text-xs text-gray-400 mb-3">Just exploring?</p>
          <Link
            href="/demo"
            className="w-full flex items-center justify-center gap-2 py-3 border-2 border-dashed border-emerald-200 rounded-xl text-sm font-semibold text-emerald-700 hover:bg-emerald-50 hover:border-emerald-300 transition-all"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Try With Sample Report — No Signup
          </Link>
          <p className="text-center text-xs text-gray-400 mt-2">
            See a full BRSR extraction from a real annual report
          </p>
        </div>
      </div>
    </div>
  );
}
