import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { QrCode, Loader2, Lock, CheckCircle2, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { apiPasswordResetConfirm } from "@/lib/api";

const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const uid = searchParams.get("uid") || "";
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  const hasMinLength = password.length >= 8;
  const hasMatch = password === confirmPassword && confirmPassword.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasMatch) {
      toast({ title: "Error", description: "Passwords do not match.", variant: "destructive" });
      return;
    }
    if (!hasMinLength) {
      toast({ title: "Error", description: "Password must be at least 8 characters.", variant: "destructive" });
      return;
    }
    setLoading(true);
    try {
      const res = await apiPasswordResetConfirm({
        uid,
        token,
        new_password1: password,
        new_password2: confirmPassword,
      });
      if (res.error) {
        toast({ title: "Error", description: res.error, variant: "destructive" });
      } else if (res.errors) {
        const msg = Object.values(res.errors).flat().join(". ");
        toast({ title: "Error", description: msg, variant: "destructive" });
      } else {
        setSuccess(true);
      }
    } catch {
      toast({ title: "Error", description: "Could not connect to server.", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  if (!uid || !token) {
    return (
      <div className="min-h-screen gradient-hero flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-card rounded-2xl shadow-elevated p-8 border text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
              <ShieldCheck className="h-8 w-8 text-destructive" />
            </div>
            <h1 className="text-2xl font-bold font-heading text-foreground mb-2">Invalid Reset Link</h1>
            <p className="text-muted-foreground mb-6">
              This password reset link is invalid or has expired. Please request a new one.
            </p>
            <Button variant="hero" className="w-full" asChild>
              <Link to="/forgot-password">Request New Link</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
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
          <div className="bg-card rounded-2xl shadow-elevated p-8 border text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <CheckCircle2 className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold font-heading text-foreground mb-2">Password Updated!</h1>
            <p className="text-muted-foreground mb-6">
              Your password has been successfully reset. You can now log in with your new password.
            </p>
            <Button variant="hero" className="w-full" onClick={() => navigate("/login")}>
              Go to Login
            </Button>
          </div>
        </div>
      </div>
    );
  }

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

        <div className="bg-card rounded-2xl shadow-elevated p-8 border">
          <div className="text-center mb-6">
            <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Lock className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold font-heading text-foreground">Create New Password</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Choose a strong password to secure your account
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="password">New Password</Label>
              <div className="relative mt-1">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter new password"
                  required
                  minLength={8}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative mt-1">
                <Input
                  id="confirmPassword"
                  type={showConfirm ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  required
                  minLength={8}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Password requirements */}
            <div className="space-y-2 text-sm">
              <div className={`flex items-center gap-2 ${hasMinLength ? "text-primary" : "text-muted-foreground"}`}>
                <CheckCircle2 className={`h-4 w-4 ${hasMinLength ? "opacity-100" : "opacity-40"}`} />
                At least 8 characters
              </div>
              <div className={`flex items-center gap-2 ${hasMatch ? "text-primary" : "text-muted-foreground"}`}>
                <CheckCircle2 className={`h-4 w-4 ${hasMatch ? "opacity-100" : "opacity-40"}`} />
                Passwords match
              </div>
            </div>

            <Button
              variant="hero"
              className="w-full"
              type="submit"
              disabled={loading || !hasMinLength || !hasMatch}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" /> Resetting...
                </>
              ) : (
                "Reset Password"
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
