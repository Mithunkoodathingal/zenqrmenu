import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CheckCircle2, ArrowRight, Settings, Utensils, QrCode, Loader2, Check } from "lucide-react";
import Navbar from "@/components/Navbar";
import { fetchRestaurantProfile } from "@/lib/restaurantApi";
import { fetchMenuItems } from "@/lib/menuApi";

type NextStep = "restaurant" | "menu" | "qr" | "dashboard";

interface StepInfo {
  key: NextStep;
  icon: typeof Settings;
  title: string;
  description: string;
  cta: string;
  route: string;
}

const STEPS: Record<Exclude<NextStep, "dashboard">, StepInfo> = {
  restaurant: {
    key: "restaurant",
    icon: Settings,
    title: "Set Up Your Restaurant",
    description: "Add your restaurant name, logo, and contact details so customers can find you.",
    cta: "Go to Restaurant Settings",
    route: "/dashboard?tab=restaurant",
  },
  menu: {
    key: "menu",
    icon: Utensils,
    title: "Create Your Menu",
    description: "Add categories and dishes so customers can browse and order from your menu.",
    cta: "Add Menu Items",
    route: "/dashboard?tab=menu",
  },
  qr: {
    key: "qr",
    icon: QrCode,
    title: "Generate Your QR Codes",
    description: "Create QR codes for your tables so customers can scan and view your menu instantly.",
    cta: "Generate QR Codes",
    route: "/dashboard?tab=qr",
  },
};

const ALL_STEPS: NextStep[] = ["restaurant", "menu", "qr"];

const PaymentSuccessPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [nextStep, setNextStep] = useState<NextStep>("dashboard");
  const [completedSteps, setCompletedSteps] = useState<Set<NextStep>>(new Set());

  useEffect(() => {
    let cancelled = false;

    const detectNextStep = async () => {
      const completed = new Set<NextStep>();
      let next: NextStep = "dashboard";

      try {
        // Step 1: Check restaurant profile
        let hasRestaurant = false;
        try {
          const profile = await fetchRestaurantProfile();
          hasRestaurant = !!profile?.name;
          if (hasRestaurant) completed.add("restaurant");
        } catch {
          hasRestaurant = false;
        }

        if (!hasRestaurant) {
          next = "restaurant";
        } else {
          // Step 2: Check menu items
          let hasMenu = false;
          try {
            const items = await fetchMenuItems();
            hasMenu = Array.isArray(items) && items.length > 0;
            if (hasMenu) completed.add("menu");
          } catch {
            hasMenu = false;
          }

          if (!hasMenu) {
            next = "menu";
          } else {
            // Step 3: Default to QR generation as the last guided step
            next = "qr";
          }
        }
      } catch {
        next = "restaurant";
      }

      if (!cancelled) {
        setCompletedSteps(completed);
        setNextStep(next);
        setLoading(false);
      }
    };

    detectNextStep();
    return () => {
      cancelled = true;
    };
  }, []);

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center gap-3 py-6">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Preparing your next step...</p>
        </div>
      );
    }

    if (nextStep === "dashboard") {
      return (
        <div className="flex flex-col gap-3">
          <Button variant="hero" className="w-full" onClick={() => navigate("/dashboard")}>
            Go to Dashboard <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
          <Link to="/">
            <Button variant="ghost" className="w-full">Back to Home</Button>
          </Link>
        </div>
      );
    }

    const step = STEPS[nextStep];
    const StepIcon = step.icon;

    return (
      <>
        {/* Progress indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {ALL_STEPS.map((s, i) => {
            const isComplete = completedSteps.has(s);
            const isActive = s === nextStep;
            return (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                    isComplete
                      ? "bg-primary text-primary-foreground"
                      : isActive
                        ? "bg-primary/20 text-primary ring-2 ring-primary"
                        : "bg-muted text-muted-foreground"
                  }`}
                >
                  {isComplete ? <Check className="h-4 w-4" /> : i + 1}
                </div>
                {i < ALL_STEPS.length - 1 && (
                  <div className={`h-0.5 w-6 ${completedSteps.has(s) ? "bg-primary" : "bg-muted"}`} />
                )}
              </div>
            );
          })}
        </div>

        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 mx-auto mb-3">
          <StepIcon className="h-7 w-7 text-primary" />
        </div>
        <h2 className="text-lg font-bold font-heading mb-2">Next: {step.title}</h2>
        <p className="text-sm text-muted-foreground mb-6">{step.description}</p>

        <div className="flex flex-col gap-3">
          <Button variant="hero" className="w-full" onClick={() => navigate(step.route)}>
            {step.cta} <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
          <Button variant="ghost" className="w-full" onClick={() => navigate("/dashboard")}>
            Skip for now — Go to Dashboard
          </Button>
        </div>
      </>
    );
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <Card className="w-full p-8 text-center shadow-elevated">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-100 mb-4">
              <CheckCircle2 className="h-8 w-8 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold font-heading mb-2">Payment Successful!</h1>
            <p className="text-muted-foreground mb-6">
              Your subscription is now active. Let's get your restaurant ready for customers.
            </p>
            {renderContent()}
          </Card>
        </motion.div>
      </main>
    </div>
  );
};

export default PaymentSuccessPage;
