import { useState, useEffect, useRef } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import AnalyticsDashboard from "@/components/dashboard/AnalyticsDashboard";
import {
  QrCode, Utensils, Settings, BarChart3, LogOut,
  ClipboardList, ChevronUp, Sparkles, Crown,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import MenuManager from "@/components/dashboard/MenuManager";
import OrdersManager from "@/components/dashboard/OrdersManager";
import QRManager from "@/components/dashboard/QRManager";
import RestaurantSettings from "@/components/dashboard/RestaurantSettings";
import OnboardingWizard from "@/components/dashboard/OnboardingWizard";
import { getStoredUser, getToken, setStoredUser, clearStoredUser, clearToken, authFetch } from "@/lib/auth";
import { apiGetUser, apiLogout } from "@/lib/api";
import { fetchOrders } from "@/lib/orderApi";
import { clearStoredSubscriptionStatus, hasActivePaidSubscription, useSubscription } from "@/hooks/useSubscription";
import { useRestaurantProfile } from "@/hooks/useRestaurantData";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.zenqrmenu.com";

const PlanBadge = () => {
  const { data: subscription } = useSubscription();
  const planName = subscription?.plan || "free";
  const isActive = hasActivePaidSubscription(subscription);
  const displayName = planName.charAt(0).toUpperCase() + planName.slice(1);

  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-2 mb-1">
        <Crown className="h-4 w-4 text-primary" />
        <span className="text-sm font-semibold text-foreground">{isActive ? `${displayName} Plan` : "Not Subscribed"}</span>
        {isActive && (
          <span className="ml-auto text-[10px] font-medium bg-primary/10 text-primary px-1.5 py-0.5 rounded-full">Active</span>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        {isActive ? `Your ${displayName} subscription is active` : "Choose a plan to unlock menu items, tables, and analytics."}
      </p>
    </div>
  );
};

type DashboardTab = "menu" | "orders" | "qr" | "restaurant" | "analytics";

const DashboardPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get("tab") as DashboardTab) || "menu";
  const [activeTab, setActiveTab] = useState<DashboardTab>(
    ["menu", "orders", "qr", "restaurant", "analytics"].includes(initialTab) ? initialTab : "menu"
  );

  // Sync ?tab= query param when it changes externally (e.g. arriving from PaymentSuccess)
  useEffect(() => {
    const t = searchParams.get("tab") as DashboardTab | null;
    if (t && ["menu", "orders", "qr", "restaurant", "analytics"].includes(t) && t !== activeTab) {
      setActiveTab(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Clear the query param after consuming it so navigation stays clean
  useEffect(() => {
    if (searchParams.get("tab")) {
      const next = new URLSearchParams(searchParams);
      next.delete("tab");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [showAccountMenu, setShowAccountMenu] = useState(false);
  const [pendingOrderCount, setPendingOrderCount] = useState(0);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const { data: restaurantProfile, isLoading: isLoadingProfile } = useRestaurantProfile();
  const { data: subscription, isLoading: isLoadingSubscription } = useSubscription();

  // Determine onboarding step
// ================= ONBOARDING LOGIC =================

// ⛔ Wait until BOTH APIs are loaded
const isReady = !isLoadingProfile && !isLoadingSubscription;

// ✅ FIX: correct data shape
const restaurant = restaurantProfile;

// 🚨 Step 1: No restaurant → MUST go to wizard
const needsRestaurantSetup =
  isReady &&
  (!restaurant || !restaurant.name);

// 🚨 Step 2: Has restaurant but no valid plan
const needsPlanSelection =
  isReady &&
  restaurant &&
  (!subscription || subscription.plan === "Free");

// 🎯 Final step
const onboardingStep: 0 | 1 | 2 =
  needsRestaurantSetup ? 1 :
  needsPlanSelection ? 2 :
  0;

console.log("STEP:", onboardingStep);
console.log("Restaurant:", restaurant);
console.log("Subscription:", subscription);


// ================= AUTH RESTORE =================

useEffect(() => {
  let cancelled = false;

  const restoreSession = async () => {
    const storedUser = getStoredUser();
    const token = getToken();

    try {
      // ✅ Always validate session from backend
      const res = await apiGetUser();
      if (cancelled) return;

      if (res && res.user) {
        const currentUser = getStoredUser();

        const currentKey =
          currentUser?.email || currentUser?.username || "";

        const nextKey =
          res.user.email || res.user.username || "";

        // 🔥 Reset subscription cache if user changed
        if (currentKey && nextKey && currentKey !== nextKey) {
          clearStoredSubscriptionStatus();
        }

        setStoredUser(res.user);
      } else {
        // ❌ Not authenticated
        if (!storedUser || !token) {
          navigate("/login", { replace: true });
          return;
        }
      }

      // ✅ Fetch menu data (safe)
      const [catRes, itemRes] = await Promise.all([
        authFetch(`${BASE_URL}/menu/api/categories/`),
        authFetch(`${BASE_URL}/menu/api/items/`)
      ]);

      if (!catRes.ok || !itemRes.ok) {
        console.warn("Menu API failed", catRes.status, itemRes.status);
      }

    } catch (err) {
      console.warn("Session restore failed:", err);

      if (!cancelled) {
        navigate("/login", { replace: true });
      }
    }
  };

  restoreSession();

  return () => {
    cancelled = true;
  };
}, [navigate]);


  // Fetch pending order count on mount & poll
  useEffect(() => {
    let cancelled = false;
    const loadCount = async () => {
      try {
        const orders = await fetchOrders();
        if (!cancelled) {
          setPendingOrderCount(orders.filter((o) => o.status === "pending").length);
        }
      } catch { /* ignore */ }
    };
    loadCount();
    const interval = setInterval(loadCount, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  // Close account menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target as Node)) {
        setShowAccountMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try { await apiLogout(); } catch { /* ignore */ }
    clearStoredSubscriptionStatus();
    clearToken();
    clearStoredUser();
    navigate("/login", { replace: true });
  };

  const storedUser = getStoredUser();

  console.log("Stored User:", storedUser); //=============================<<< ERROR LOGGING IN CONSOLE =========

  const accountLabel =
    storedUser?.username?.trim() ||
    storedUser?.email?.split("@")[0] ||
    "User";
    

  const sidebarItems = [
    { key: "menu" as const, icon: Utensils, label: "Manage Menu" },
    { key: "orders" as const, icon: ClipboardList, label: "View Orders" },
    { key: "qr" as const, icon: QrCode, label: "Generate QR" },
    { key: "restaurant" as const, icon: Settings, label: "Restaurant" },
    { key: "analytics" as const, icon: BarChart3, label: "Analytics" },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Sidebar — fixed */}
      <aside className="w-64 border-r bg-card hidden lg:flex flex-col fixed top-0 left-0 h-screen z-40">
        <div className="p-4 border-b">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg gradient-primary">
              <QrCode className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold font-heading text-gradient">zen menu</span>
          </Link>
        </div>
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {sidebarItems.map((item) => (
            <button
              key={item.key}
              onClick={() => setActiveTab(item.key)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === item.key
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
              {item.key === "orders" && pendingOrderCount > 0 && (
                <span className="ml-auto h-5 w-5 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-bold">{pendingOrderCount}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="p-3 border-t relative" ref={accountMenuRef}>
          {/* Pop-up menu */}
          {showAccountMenu && (
            <div className="absolute bottom-full left-3 right-3 mb-2 bg-popover border rounded-lg shadow-lg animate-fade-in overflow-hidden">
              {/* Current Plan Display */}
              <PlanBadge />
              <div className="border-t" />
              <Link
                to="/pricing"
                onClick={() => setShowAccountMenu(false)}
                className="flex items-center gap-3 px-4 py-3 text-sm font-medium hover:bg-muted transition-colors"
              >
                <Sparkles className="h-4 w-4 text-primary" />
                <span>{hasActivePaidSubscription(subscription) ? "Upgrade Plan" : "Subscribe Now"}</span>
              </Link>
              <div className="border-t" />
              <button
                onClick={() => { setShowAccountMenu(false); handleLogout(); }}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-destructive hover:bg-muted transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Log Out
              </button>
            </div>
          )}
          <button
            onClick={() => setShowAccountMenu(!showAccountMenu)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <div className="h-7 w-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-foreground ring-2 ring-primary">
              {(accountLabel[0] || "Z").toUpperCase()}
            </div>
            <span className="flex-1 text-left truncate">{accountLabel}</span>
            <ChevronUp className={`h-4 w-4 transition-transform shrink-0 ${showAccountMenu ? "rotate-180" : ""}`} />
          </button>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-card border-b">
        <div className="flex items-center justify-between p-3">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg gradient-primary">
              <QrCode className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold font-heading text-gradient">zen menu</span>
          </Link>
          <button
            onClick={handleLogout}
            className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-muted transition-colors"
            title="Log out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
        <div className="flex items-center border-t">
          <button
            onClick={() => {
              const idx = sidebarItems.findIndex(i => i.key === activeTab);
              if (idx > 0) setActiveTab(sidebarItems[idx - 1].key);
            }}
            className="shrink-0 px-2 py-2.5 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30"
            disabled={activeTab === sidebarItems[0].key}
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="flex-1 flex justify-center">
            {sidebarItems.map((item) => (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key)}
                className={`flex items-center justify-center gap-1 px-3 py-2.5 text-xs font-medium transition-colors whitespace-nowrap ${
                  activeTab === item.key ? "text-primary border-b-2 border-primary" : "text-muted-foreground"
                }`}
              >
                <item.icon className="h-3.5 w-3.5" />
                <span className="hidden xs:inline">{item.label}</span>
              </button>
            ))}
          </div>
          <button
            onClick={() => {
              const idx = sidebarItems.findIndex(i => i.key === activeTab);
              if (idx < sidebarItems.length - 1) setActiveTab(sidebarItems[idx + 1].key);
            }}
            className="shrink-0 px-2 py-2.5 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30"
            disabled={activeTab === sidebarItems[sidebarItems.length - 1].key}
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Main */}
      <main className="flex-1 lg:ml-64 lg:p-8 p-4 pt-28 lg:pt-8 overflow-auto">
      

        {/* ⛔ WAIT until data is ready */}
        {!isReady ? (
          <div>Loading...</div>
        ) : onboardingStep > 0 ? (

          activeTab === "restaurant" ? (
            <RestaurantSettings onSavedFirstTime={() => setActiveTab("menu")} />
          ) : (
            <OnboardingWizard
              currentStep={onboardingStep as 1 | 2}
              onGoToRestaurant={() => setActiveTab("restaurant")}
            />
          )

        ) : (

          <>
            {activeTab === "menu" && <MenuManager />}
            {activeTab === "orders" && <OrdersManager />}
            {activeTab === "qr" && <QRManager />}
            {activeTab === "restaurant" && <RestaurantSettings />}
            {activeTab === "analytics" && <AnalyticsDashboard />}
          </>
        )}

      </main>
    </div>
  );
};

export default DashboardPage;
