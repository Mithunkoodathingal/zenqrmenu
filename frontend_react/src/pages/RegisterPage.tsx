import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { QrCode, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRegister } from "@/lib/api";
import GoogleSignInButton from "@/components/GoogleSignInButton";

const RegisterPage = () => {
  const [form, setForm] = useState({ username: "", email: "", password1: "", password2: "" });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const navigate = useNavigate();
  const { toast } = useToast();

  const update = (key: string, value: string) => setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    if (form.password1 !== form.password2) {
      setErrors({ password2: ["Passwords do not match"] });
      return;
    }

    setLoading(true);
    try {
      const res = await apiRegister(form);
      if (res.success) {
        toast({ title: "Account Created!", description: "Please verify your email to continue." });
        navigate("/verify-email", { state: { email: form.email } });
      } else if (res.errors) {
        setErrors(res.errors);
      } else {
        toast({ title: "Error", description: res.message || "Registration failed.", variant: "destructive" });
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

        <div className="bg-card rounded-xl shadow-elevated p-8 border">
          <h1 className="text-2xl font-bold font-heading text-center text-primary mb-6">Create Account</h1>

          <GoogleSignInButton />

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
            <div className="relative flex justify-center text-xs uppercase"><span className="bg-card px-2 text-muted-foreground">or</span></div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username">Username</Label>
              <Input id="username" value={form.username} onChange={(e) => update("username", e.target.value)} placeholder="johndoe" className="mt-1" required />
              {errors.username?.map((e) => <p key={e} className="text-destructive text-xs mt-1">{e}</p>)}
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} placeholder="you@restaurant.com" className="mt-1" required />
              {errors.email?.map((e) => <p key={e} className="text-destructive text-xs mt-1">{e}</p>)}
            </div>
            <div>
              <Label htmlFor="password1">Password</Label>
              <Input id="password1" type="password" value={form.password1} onChange={(e) => update("password1", e.target.value)} placeholder="••••••••" className="mt-1" required />
              {errors.password1?.map((e) => <p key={e} className="text-destructive text-xs mt-1">{e}</p>)}
            </div>
            <div>
              <Label htmlFor="password2">Confirm Password</Label>
              <Input id="password2" type="password" value={form.password2} onChange={(e) => update("password2", e.target.value)} placeholder="••••••••" className="mt-1" required />
              {errors.password2?.map((e) => <p key={e} className="text-destructive text-xs mt-1">{e}</p>)}
            </div>
            <Button variant="hero" className="w-full" type="submit" disabled={loading}>
              {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Creating...</> : "Create Account"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="text-primary font-semibold hover:underline">Log In</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
