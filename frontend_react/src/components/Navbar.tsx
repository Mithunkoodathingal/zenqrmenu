import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Menu, X, QrCode } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getToken, clearToken, clearStoredUser } from "@/lib/auth";
import { apiLogout } from "@/lib/api";
import { clearStoredSubscriptionStatus } from "@/hooks/useSubscription";

const navItems = [
  { label: "Home", path: "/" },
  { label: "Features", path: "/#features" },
  { label: "How It Works", path: "/#how-it-works" },
  { label: "Pricing", path: "/pricing" },
  { label: "Contact", path: "/contact" },
];

const Navbar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const isLoggedIn = !!getToken();

  const scrollToSection = (hash: string) => {
    setMobileOpen(false);
    if (location.pathname !== "/") return;
    const el = document.querySelector(hash);
    el?.scrollIntoView({ behavior: "smooth" });
  };

  const handleLogout = async () => {
    setMobileOpen(false);
    try { await apiLogout(); } catch { /* ignore */ }
    clearStoredSubscriptionStatus();
    clearToken();
    clearStoredUser();
    navigate("/login", { replace: true });
  };

  return (
    <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-lg">
      <div className="container flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg gradient-primary">
            <QrCode className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-bold font-heading text-gradient">zen menu</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          {navItems.map((item) => (
            <button
              key={item.label}
              onClick={() => {
                if (item.path.includes("#")) {
                  scrollToSection(item.path.replace("/", ""));
                }
              }}
              className={cn(
                "text-sm font-medium text-muted-foreground hover:text-primary transition-colors",
                location.pathname === item.path && "text-primary"
              )}
            >
              {item.path.includes("#") ? (
                item.label
              ) : (
                <Link to={item.path}>{item.label}</Link>
              )}
            </button>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          {isLoggedIn ? (
            <>
              <Link to="/dashboard">
                <Button variant="ghost" size="sm">Dashboard</Button>
              </Link>
              <Button variant="hero" size="sm" onClick={handleLogout}>Log Out</Button>
            </>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost" size="sm">Log In</Button>
              </Link>
              <Link to="/register">
                <Button variant="hero" size="sm">Get Started Free</Button>
              </Link>
            </>
          )}
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden p-2 text-foreground"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t bg-background animate-fade-in">
          <div className="container py-4 flex flex-col gap-3">
            {navItems.map((item) => (
              <button
                key={item.label}
                onClick={() => {
                  if (item.path.includes("#")) {
                    scrollToSection(item.path.replace("/", ""));
                  }
                }}
                className="text-sm font-medium text-muted-foreground hover:text-primary py-2 text-left"
              >
                {item.path.includes("#") ? (
                  item.label
                ) : (
                  <Link to={item.path} onClick={() => setMobileOpen(false)}>{item.label}</Link>
                )}
              </button>
            ))}
            <div className="flex gap-3 pt-2">
              {isLoggedIn ? (
                <>
                  <Link to="/dashboard" className="flex-1" onClick={() => setMobileOpen(false)}>
                    <Button variant="outline" className="w-full">Dashboard</Button>
                  </Link>
                  <Button variant="hero" className="flex-1" onClick={handleLogout}>Log Out</Button>
                </>
              ) : (
                <>
                  <Link to="/login" className="flex-1">
                    <Button variant="outline" className="w-full">Log In</Button>
                  </Link>
                  <Link to="/register" className="flex-1">
                    <Button variant="hero" className="w-full">Get Started</Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
