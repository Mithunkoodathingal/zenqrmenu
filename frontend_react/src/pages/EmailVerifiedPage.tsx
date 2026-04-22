import { Link } from "react-router-dom";
import { QrCode, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const EmailVerifiedPage = () => {
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
            <CheckCircle2 className="h-8 w-8 text-primary" />
          </div>

          <h1 className="text-2xl font-bold font-heading text-primary mb-2">Email Verified!</h1>
          <p className="text-muted-foreground mb-6">
            Your email has been successfully verified. You can now log in to your account.
          </p>

          <Button variant="hero" className="w-full" asChild>
            <Link to="/login">Continue to Login</Link>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default EmailVerifiedPage;
