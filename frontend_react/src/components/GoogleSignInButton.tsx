import { useEffect, useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { setToken, setRefreshToken, setStoredUser } from "@/lib/auth";
import { apiGetUser } from "@/lib/api";
import { clearStoredSubscriptionStatus } from "@/hooks/useSubscription";
import { Loader2 } from "lucide-react";

const GOOGLE_CLIENT_ID = "886773285585-fg35vj7ot1884qvkp64q9l7n8gst3tfn.apps.googleusercontent.com";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.zenqrmenu.com";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (element: HTMLElement, config: Record<string, unknown>) => void;
        };
      };
    };
  }
}

export default function GoogleSignInButton() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleCredentialResponse = useCallback(
    async (response: { credential: string }) => {
      setLoading(true);
      try {
        const res = await fetch(`${BASE_URL}/api/auth/google/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id_token: response.credential }),
        });

        const contentType = res.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
          throw new Error("Invalid response from server");
        }

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || data.detail || "Google login failed");
        }

        // ✅ Store tokens
        const accessToken = data.access;
          if (accessToken) setToken(accessToken);
          if (data.refresh) setRefreshToken(data.refresh);

        const user =
          data.user ??
          (await apiGetUser()
            .then((session) => session.user)
            .catch(() => undefined)) ??
          { username: data.email || "User", email: data.email || "" };

        clearStoredSubscriptionStatus();
        setStoredUser(user);

        toast({ title: "Welcome!", description: `Signed in as ${user.email || user.username}` });
        navigate("/dashboard");
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Google sign-in failed";
        toast({ title: "Error", description: message, variant: "destructive" });
      } finally {
        setLoading(false);
      }
    },
    [navigate, toast]
  );

  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      window.google?.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
      });

      const btnEl = document.getElementById("google-signin-btn");
      if (btnEl) {
        const btnWidth = Math.min(btnEl.offsetWidth || 320, 400);
        window.google?.accounts.id.renderButton(btnEl, {
          theme: "outline",
          size: "large",
          width: String(btnWidth),
          text: "continue_with",
          shape: "rectangular",
          logo_alignment: "center",
        });
      }
    };
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, [handleCredentialResponse]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-3">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Signing in with Google...</span>
      </div>
    );
  }

  return (
    <div className="w-full flex justify-center px-2">
      <div id="google-signin-btn" className="w-full max-w-[400px]" />
    </div>
  );
}
