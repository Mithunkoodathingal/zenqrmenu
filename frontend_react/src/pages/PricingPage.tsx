import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Check, Loader2, Crown, Zap, Building2, Star } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { fetchPlans, createSubscription, verifyPayment, normalizePlan, type Plan } from "@/lib/api";
import { loadRazorpayScript, openRazorpayCheckout } from "@/lib/razorpay";
import { getToken } from "@/lib/auth";
import { hasActivePaidSubscription, persistPlanSubscription, useSubscription } from "@/hooks/useSubscription";

const iconMap: Record<string, React.ElementType> = {
  Free: Zap,
  Basic: Star,
  Standard: Crown,
  Pro: Crown,
  Enterprise: Building2,
};

const fallbackPlans: Plan[] = [
  {
    id: "free",
    name: "Free",
    price: 0,
    period: "/month",
    features: ["1 Restaurant", "Unlimited items", "1 QR code", "Basic analytics"],
  },
  {
    id: "basic",
    name: "Basic",
    price: 100,
    period: "/month",
    features: [
      "Unlimited scans",
      "Unlimited categories & items",
      "Up to 10 QR codes",
    ],
    popular: true,
  },
  {
    id: "standard",
    name: "Standard",
    price: 200,
    period: "/month",
    features: [
      "Unlimited scans",
      "Unlimited categories & items",
      "Up to 20 QR codes",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: 500,
    period: "/month",
    features: [
      "Ideal for hotels",
      "Unlimited scans",
      "Unlimited categories & items",
      "Up to 100 QR codes",
    ],
  },
];

const normalizePlanName = (value?: string | null) => value?.trim().toLowerCase() ?? "";

const PLAN_RANK: Record<string, number> = {
  free: 0,
  basic: 1,
  pro: 1,
  standard: 2,
  enterprise: 3,
};

const getPlanRank = (name: string) => PLAN_RANK[normalizePlanName(name)] ?? 0;

const PLAN_ALIASES: Record<string, string[]> = {
  free: ["free"],
  basic: ["basic", "pro"],
  standard: ["standard"],
  enterprise: ["enterprise"],
};

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] as const },
  }),
};

const PricingPage = () => {
  const [plans, setPlans] = useState<Plan[]>(fallbackPlans);
  const [loading, setLoading] = useState(true);
  const [payingPlanId, setPayingPlanId] = useState<string | number | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: subscription } = useSubscription();
  const activePlan = hasActivePaidSubscription(subscription) ? normalizePlanName(subscription?.plan) : null;
  const isLoggedIn = !!getToken();

  useEffect(() => {
    fetchPlans()
      .then((data) => {
        if (data && data.length > 0) setPlans(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const normalizedPlans = useMemo(() => plans.map(normalizePlan), [plans]);

  const isCurrentPlanCheck = (planName: string) => {
    const n = normalizePlanName(planName);
    return !!activePlan && (PLAN_ALIASES[n] ?? [n]).includes(activePlan);
  };

  const isLowerPlan = (planName: string) => {
    if (!activePlan) return false;
    return getPlanRank(planName) < (PLAN_RANK[activePlan] ?? 0);
  };

  const handleSubscribe = async (plan: Plan) => {
    if (isLowerPlan(plan.name)) {
      toast({ title: "Cannot Downgrade", description: "You cannot switch to a lower plan. Contact support if needed.", variant: "destructive" });
      return;
    }

    if (plan.name === "Free") {
      if (!isLoggedIn) {
        navigate("/register");
        return;
      }
      // Logged-in user on Free plan — fall through to createSubscription to activate it
    }
    if (plan.name === "Enterprise" && plan.price === 0) {
      window.location.href = "mailto:hello@zenqrmenu.com?subject=Enterprise%20Plan%20Inquiry";
      return;
    }

    setPayingPlanId(plan.id);

    try {
      const order = await createSubscription(plan.id);

      if (order.free) {
        persistPlanSubscription(plan);
        toast({ title: "Success!", description: "Free plan activated successfully." });
        navigate("/payment-success");
        setPayingPlanId(null);
        return;
      }

      const loaded = await loadRazorpayScript();
      if (!loaded) {
        toast({ title: "Error", description: "Failed to load payment gateway. Please try again.", variant: "destructive" });
        setPayingPlanId(null);
        return;
      }

      openRazorpayCheckout(order, {
        onSuccess: async (response) => {
          try {
            await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            persistPlanSubscription(plan);
            navigate("/payment-success");
          } catch {
            navigate("/payment-failure");
          }
        },
        onFailure: () => {
          toast({ title: "Payment Cancelled", description: "You cancelled the payment. No charges were made.", variant: "destructive" });
          setPayingPlanId(null);
        },
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.message === "LOGIN_REQUIRED") {
        toast({ title: "Login Required", description: "Please log in to subscribe to a plan.", variant: "destructive" });
        navigate("/login");
      } else {
        const message = err instanceof Error ? err.message : "Could not initiate payment. Please try again.";
        toast({ title: "Subscription Error", description: message, variant: "destructive" });
      }
    } finally {
      setPayingPlanId(null);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 py-20 lg:py-28">
        <div className="container">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={0}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h1 className="text-3xl md:text-5xl font-extrabold font-heading">
              Simple, <span className="text-gradient">Transparent Pricing</span>
            </h1>
            <p className="mt-4 text-muted-foreground text-lg">
              Start free and upgrade as your business grows. No hidden fees, cancel anytime.
            </p>
          </motion.div>

          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <div className={`grid gap-8 max-w-5xl mx-auto ${normalizedPlans.length === 4 ? 'md:grid-cols-2 lg:grid-cols-4' : 'md:grid-cols-3'}`}>
                {normalizedPlans.map((plan, i) => {
                const Icon = iconMap[plan.name] || Zap;
                const isPaying = payingPlanId === plan.id;
                const isCurrentPlan = isCurrentPlanCheck(plan.name);
                const isLower = isLowerPlan(plan.name);

                return (
                  <motion.div
                    key={plan.id}
                    initial="hidden"
                    animate="visible"
                    variants={fadeUp}
                    custom={i + 1}
                  >
                    <Card
                      className={`relative p-8 flex flex-col h-full transition-all duration-300 hover:shadow-elevated ${
                        isCurrentPlan
                          ? "border-primary border-2 ring-2 ring-primary/20 shadow-elevated"
                          : plan.popular
                          ? "border-primary border-2 shadow-elevated scale-[1.02]"
                          : "shadow-card"
                      }`}
                    >
                      {isCurrentPlan && (
                        <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 gradient-primary text-primary-foreground text-xs font-bold px-5 py-1.5 rounded-full shadow-sm">
                          Current Plan
                        </span>
                      )}
                      {!isCurrentPlan && plan.popular && (
                        <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 gradient-primary text-primary-foreground text-xs font-bold px-5 py-1.5 rounded-full shadow-sm">
                          Most Popular
                        </span>
                      )}

                      <div className="flex items-center gap-3 mb-6">
                        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${plan.popular || isCurrentPlan ? "gradient-primary" : "bg-accent"}`}>
                          <Icon className={`h-5 w-5 ${plan.popular || isCurrentPlan ? "text-primary-foreground" : "text-accent-foreground"}`} />
                        </div>
                        <h3 className="text-xl font-bold">{plan.name}</h3>
                      </div>

                      <div className="mb-6">
                        {plan.price > 0 ? (
                          <>
                            <span className="text-4xl font-extrabold">₹{plan.price}</span>
                            <span className="text-muted-foreground">{plan.period}</span>
                          </>
                        ) : plan.name === "Enterprise" && plan.price === 0 ? (
                          <span className="text-4xl font-extrabold">Custom</span>
                        ) : (
                          <>
                            <span className="text-4xl font-extrabold">₹0</span>
                            <span className="text-muted-foreground">/month</span>
                          </>
                        )}
                      </div>

                      <ul className="space-y-3 mb-8 flex-1">
                        {plan.table_limit && (
                          <li className="flex items-start gap-2.5 text-sm">
                            <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                            <span className="text-muted-foreground">Up to {plan.table_limit} tables</span>
                          </li>
                        )}
                        {plan.features.map((f) => (
                          <li key={f} className="flex items-start gap-2.5 text-sm">
                            <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                            <span className="text-muted-foreground">{f}</span>
                          </li>
                        ))}
                      </ul>

                      <Button
                        variant={isCurrentPlan || isLower ? "outline" : plan.popular ? "hero" : "outline"}
                        className="w-full"
                        onClick={() => handleSubscribe(plan)}
                        disabled={isPaying || isCurrentPlan || isLower}
                      >
                        {isPaying ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            Processing...
                          </>
                        ) : isCurrentPlan ? (
                          "✓ Active Plan"
                        ) : isLower ? (
                          "Current Plan is Higher"
                        ) : plan.name === "Free" && !activePlan && !isLoggedIn ? (
                          "Start Free"
                        ) : plan.name === "Enterprise" && plan.price === 0 ? (
                          "Contact Us"
                        ) : activePlan ? (
                          "Upgrade"
                        ) : isLoggedIn ? (
                          "Subscribe"
                        ) : (
                          "Subscribe Now"
                        )}
                      </Button>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          )}

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
            className="mt-20 text-center max-w-2xl mx-auto"
          >
            <p className="text-sm text-muted-foreground">
              🔒 Payments secured by Razorpay • Cancel anytime • No hidden charges
            </p>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default PricingPage;
