import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowRight, QrCode, Utensils, BarChart3, Smartphone } from "lucide-react";
import heroImage from "@/assets/hero-illustration.jpg";
import menuPhone from "@/assets/menu-phone.jpg";
import qrScan from "@/assets/qr-scan.jpg";
import dashboardManage from "@/assets/dashboard-manage.jpg";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { fetchPlans, normalizePlan } from "@/lib/api";


//=================FEATURES==================

const features = [
  {
    icon: QrCode,
    title: "Generate QR Codes",
    description: "Create unique QR codes for each table in your restaurant. Print them and place them on tables for instant access.",
  },
  {
    icon: Utensils,
    title: "Manage Your Menu",
    description: "Add, edit, and organize your menu items with categories, prices, descriptions, and images — all in real time.",
  },
  {
    icon: Smartphone,
    title: "Mobile-First Experience",
    description: "Your customers scan the QR code and instantly see a beautiful, fast-loading digital menu on their phones.",
  },
  {
    icon: BarChart3,
    title: "Track & Analyze",
    description: "Get insights into which items are viewed most, peak hours, and customer engagement analytics.",
  },
];

const steps = [
  {
    step: "01",
    title: "Register Your Restaurant",
    description: "Sign up and add your restaurant details — name, logo, address, and cuisine type.",
    image: dashboardManage,
  },
  {
    step: "02",
    title: "Create Your Digital Menu",
    description: "Add categories and items with photos, descriptions, and prices. Organize however you like.",
    image: menuPhone,
  },
  {
    step: "03",
    title: "Generate Table QR Codes",
    description: "Generate unique QR codes for each table. Download, print, and place them for your diners.",
    image: qrScan,
  },
];

const fallbackPlans = [
  { name: "Free", price: "₹0", period: "/month", features: ["1 Restaurant", "Up to 20 menu items", "5 QR codes", "Basic analytics"], cta: "Start Free", popular: false },
  { name: "Basic", price: "₹100", period: "/month", features: ["Unlimited scans", "Unlimited categories & items", "Up to 10 QR codes"], cta: "Subscribe", popular: true },
  { name: "Standard", price: "₹200", period: "/month", features: ["Unlimited scans", "Unlimited categories & items", "Up to 20 QR codes"], cta: "Subscribe", popular: false },
  { name: "Enterprise", price: "₹500", period: "/month", features: ["Ideal for hotels", "Unlimited scans", "Unlimited categories & items", "Up to 100 QR codes"], cta: "Subscribe", popular: false },
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] as const },
  }),
};

const LandingPage = () => {
  const [plans, setPlans] = useState(fallbackPlans);

  useEffect(() => {
    fetchPlans()
      .then((data) => {
        if (data && data.length > 0) {
          setPlans(
            data.map((p) => {
              const np = normalizePlan(p);
              const features = typeof np.features === "string" ? np.features.split(",").map((f: string) => f.trim()) : [...np.features];
              if (np.table_limit && !features.some(f => /table|qr/i.test(f))) {
                features.push(`Up to ${np.table_limit} QR codes`);
              }
              return {
                name: np.name,
                price: np.price > 0 ? `₹${np.price}` : np.name === "Enterprise" ? "Custom" : "₹0",
                period: np.period || "/month",
                features,
                cta: np.name === "Free" ? "Start Free" : np.name === "Enterprise" && np.price === 0 ? "Contact Us" : "Subscribe",
                popular: np.popular ?? false,
              };
            })
          );
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Hero */}
      <section className="gradient-hero">
        <div className="container py-20 lg:py-28">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold font-heading leading-tight tracking-tight">
                Digital Menus,{" "}
                <span className="text-gradient">Made Simple</span>
              </h1>
              <p className="mt-6 text-lg text-muted-foreground max-w-lg">
                Create beautiful QR code menus for your restaurant in minutes. 
                Go contactless, reduce printing costs, and update your menu anytime — from anywhere.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link to="/register">
                  <Button variant="hero" size="lg" className="text-base px-8">
                    Get Started Free <ArrowRight className="ml-1 h-4 w-4" />
                  </Button>
                </Link>
                <a href="#how-it-works">
                  <Button variant="hero-outline" size="lg" className="text-base px-8">
                    See How It Works
                  </Button>
                </a>
              </div>
              <p className="mt-4 text-sm text-muted-foreground">No credit card required • Free forever plan</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative"
            >
              <img
                src={heroImage}
                alt="Restaurant waiter showing digital QR menu to diners"
                width={1024}
                height={768}
                className="rounded-2xl shadow-elevated"
              />
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 lg:py-28">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-50px" }}
            variants={fadeUp}
            custom={0}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold font-heading">
              Everything You Need to Go <span className="text-gradient">Digital</span>
            </h2>
            <p className="mt-4 text-muted-foreground text-lg">
              Powerful tools to create, manage, and share your restaurant menu with ease.
            </p>
          </motion.div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-30px" }}
                variants={fadeUp}
                custom={i}
                className="group rounded-xl border bg-card p-6 shadow-card hover:shadow-elevated transition-shadow"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent mb-4">
                  <feature.icon className="h-6 w-6 text-accent-foreground" />
                </div>
                <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 lg:py-28 bg-muted/50">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold font-heading">
              Get Started in <span className="text-gradient">3 Easy Steps</span>
            </h2>
            <p className="mt-4 text-muted-foreground text-lg">
              From signup to serving digital menus — it takes less than 10 minutes.
            </p>
          </motion.div>

          <div className="space-y-16">
            {steps.map((step, i) => (
              <motion.div
                key={step.step}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-50px" }}
                variants={fadeUp}
                custom={i}
                className={`grid lg:grid-cols-2 gap-10 items-center ${i % 2 === 1 ? "lg:direction-rtl" : ""}`}
              >
                <div className={i % 2 === 1 ? "lg:order-2" : ""}>
                  <span className="text-5xl font-extrabold text-gradient opacity-40">{step.step}</span>
                  <h3 className="text-2xl font-bold mt-2 mb-3">{step.title}</h3>
                  <p className="text-muted-foreground text-lg">{step.description}</p>
                </div>
                <div className={i % 2 === 1 ? "lg:order-1" : ""}>
                  <img
                    src={step.image}
                    alt={step.title}
                    loading="lazy"
                    width={512}
                    height={512}
                    className="rounded-xl shadow-card w-full max-w-md mx-auto"
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-20 lg:py-28">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
            className="text-center max-w-2xl mx-auto mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold font-heading">
              Simple, <span className="text-gradient">Transparent Pricing</span>
            </h2>
            <p className="mt-4 text-muted-foreground text-lg">
              Start free and upgrade as your business grows.
            </p>
          </motion.div>

          <div className={`grid gap-8 max-w-5xl mx-auto ${plans.length === 4 ? 'md:grid-cols-2 lg:grid-cols-4' : 'md:grid-cols-3'}`}>
            {plans.map((plan, i) => (
              <motion.div
                key={plan.name}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i}
                className={`rounded-xl border p-8 flex flex-col ${
                  plan.popular
                    ? "border-primary shadow-elevated relative bg-card"
                    : "bg-card shadow-card"
                }`}
              >
                {plan.popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 gradient-primary text-primary-foreground text-xs font-semibold px-4 py-1 rounded-full">
                    Most Popular
                  </span>
                )}
                <h3 className="text-xl font-bold">{plan.name}</h3>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-extrabold">{plan.price}</span>
                  <span className="text-muted-foreground">{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-accent-foreground text-xs">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link to="/pricing">
                  <Button
                    variant={plan.popular ? "hero" : "outline"}
                    className="w-full"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 gradient-primary">
        <div className="container text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-primary-foreground font-heading">
            Ready to Modernize Your Menu?
          </h2>
          <p className="mt-4 text-primary-foreground/80 text-lg max-w-lg mx-auto">
            Join hundreds of restaurants already using Zen Menu to serve their customers a better dining experience.
          </p>
          <Link to="/register">
            <Button variant="hero-outline" size="lg" className="mt-8 border-primary-foreground text-primary-foreground hover:bg-primary-foreground/10">
              Get Started Free <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default LandingPage;
