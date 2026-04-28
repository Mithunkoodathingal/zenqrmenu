import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { QrCode, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiLogin, apiGetUser } from "@/lib/api";
import { setToken, setRefreshToken, setStoredUser } from "@/lib/auth";
import { clearStoredSubscriptionStatus } from "@/hooks/useSubscription";
import GoogleSignInButton from "@/components/GoogleSignInButton";

const LoginPage = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiLogin({ username, password });

      // Handle email not verified (403)
      if (res.error === "Email not verified") {
        navigate("/verify-email", { state: { email: res.email || "" } });
        return;
      }

      if (res.error) {
        toast({ title: "Login Failed", description: res.error, variant: "destructive" });
        return;
      }

      // Store tokens
      const accessToken = res.access ?? res.token ?? res.access_token ?? res.jwt;
      if (accessToken) setToken(accessToken);
      if (res.refresh) setRefreshToken(res.refresh);

      const user =
        res.user ??
        (await apiGetUser()
          .then((session) => session.user)
          .catch(() => undefined)) ??
        { username, email: "" };

      clearStoredSubscriptionStatus();
      setStoredUser(user);
      toast({ title: "Welcome back!", description: `Logged in as ${user.email || user.username}` });
      navigate("/dashboard");
    } catch {
      toast({ title: "Error", description: "Could not connect to server.", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gradient-hero flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg gradient-primary">
              <QrCode className="h-6 w-6 text-primary-foreground" />
            </div>
            <span className="text-2xl font-bold font-heading text-gradient">zen menu</span>
          </Link>
        </div>

        <div className="bg-card rounded-xl shadow-elevated p-8 border">
          <h1 className="text-2xl font-bold font-heading text-center text-primary mb-6">Log In</h1>

          <GoogleSignInButton />

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
            <div className="relative flex justify-center text-xs uppercase"><span className="bg-card px-2 text-muted-foreground">or</span></div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username">Username or Email</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="johndoe or you@email.com"
                className="mt-1"
                required
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1"
                required
              />
            </div>
            <Button variant="hero" className="w-full" type="submit" disabled={loading}>
              {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Logging in...</> : "Log In"}
            </Button>
          </form>

          <div className="mt-4 text-center">
            <Link to="/forgot-password" className="text-sm text-primary hover:underline">Forgot password?</Link>
          </div>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Don't have an account?{" "}
            <Link to="/register" className="text-primary font-semibold hover:underline">Sign Up</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
