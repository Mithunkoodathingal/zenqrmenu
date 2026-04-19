import { useState } from "react";
import { Link } from "react-router-dom";
import { QrCode, Loader2, Mail, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { apiPasswordReset } from "@/lib/api";

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiPasswordReset(email);
      if (res.error) {
        toast({ title: "Error", description: res.error, variant: "destructive" });
      } else {
        setSent(true);
      }
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

        <div className="bg-card rounded-xl shadow-elevated p-8 border text-center">
          {sent ? (
            <>
              <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Mail className="h-8 w-8 text-primary" />
              </div>
              <h1 className="text-2xl font-bold font-heading text-primary mb-2">Check Your Email</h1>
              <p className="text-muted-foreground mb-2">
                We've sent a password reset link to
              </p>
              <p className="font-semibold text-foreground mb-4">{email}</p>
              <p className="text-muted-foreground text-sm mb-6">
                Click the link in the email to reset your password. Check your spam folder if you don't see it.
              </p>
              <Button variant="hero" className="w-full" asChild>
                <Link to="/login">Back to Login</Link>
              </Button>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-bold font-heading text-primary mb-2">Forgot Password?</h1>
              <p className="text-muted-foreground text-sm mb-6">
                Enter your email address and we'll send you a link to reset your password.
              </p>
              <form onSubmit={handleSubmit} className="space-y-4 text-left">
                <div>
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@email.com"
                    className="mt-1"
                    required
                  />
                </div>
                <Button variant="hero" className="w-full" type="submit" disabled={loading}>
                  {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Sending...</> : "Send Reset Link"}
                </Button>
              </form>
            </>
          )}

          <div className="mt-4">
            <Link to="/login" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
              <ArrowLeft className="h-3 w-3" /> Back to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
