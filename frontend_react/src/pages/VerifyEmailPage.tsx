import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { QrCode, MailCheck, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { apiResendVerification } from "@/lib/api";

const VerifyEmailPage = () => {
  const location = useLocation();
  const email = (location.state as { email?: string })?.email || "";
  const [resending, setResending] = useState(false);
  const { toast } = useToast();

  const handleResend = async () => {
    if (!email) {
      toast({ title: "Error", description: "No email address available. Please register again.", variant: "destructive" });
      return;
    }
    setResending(true);
    try {
      const res = await apiResendVerification(email);
      if (res.error) {
        toast({ title: "Error", description: res.error, variant: "destructive" });
      } else {
        toast({ title: "Email Sent!", description: res.message || "Verification email has been resent." });
      }
    } catch {
      toast({ title: "Error", description: "Could not connect to server.", variant: "destructive" });
    } finally {
      setResending(false);
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
          <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <MailCheck className="h-8 w-8 text-primary" />
          </div>

          <h1 className="text-2xl font-bold font-heading text-primary mb-2">Check Your Email</h1>

          <p className="text-muted-foreground mb-2">
            We've sent a verification link to
          </p>
          {email && (
            <p className="font-semibold text-foreground mb-4">{email}</p>
          )}
          <p className="text-muted-foreground text-sm mb-6">
            Please click the link in the email to verify your account. Once verified, you can log in.
          </p>

          <div className="space-y-3">
            <Button variant="hero" className="w-full" asChild>
              <Link to="/login">Go to Login</Link>
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={handleResend}
              disabled={resending || !email}
            >
              {resending ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Resending...</> : "Resend Verification Email"}
            </Button>
            <p className="text-xs text-muted-foreground">
              Didn't receive the email? Check your spam folder or click resend above.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmailPage;
