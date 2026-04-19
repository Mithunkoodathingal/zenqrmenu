import { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Mail,
  Phone,
  MapPin,
  MessageCircle,
  ArrowRight,
  Send,
  Star,
  CheckCircle2,
  Clock,
  Users,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { toast } from "sonner";

const WHATSAPP_NUMBER = "918921367476";
const WHATSAPP_LINK = `https://wa.me/${WHATSAPP_NUMBER}`;

const contactMethods = [
  {
    icon: Mail,
    title: "Email Us",
    detail: "hello@zenqrmenu.com",
    description: "For support & sales enquiries",
    href: "mailto:hello@zenqrmenu.com",
  },
  {
    icon: Phone,
    title: "WhatsApp Only",
    detail: "+91-8921367476",
    description: "Quick replies, Mon–Sat 10am–7pm",
    href: WHATSAPP_LINK,
  },
  {
    icon: MessageCircle,
    title: "Live Chat",
    detail: "Chat on WhatsApp",
    description: "Instant support via WhatsApp",
    href: `${WHATSAPP_LINK}?text=${encodeURIComponent("Hi, I'd like to know more about Zen Menu!")}`,
  },
  {
    icon: MapPin,
    title: "Office Address",
    detail: "Gokulam, Mysore",
    description: "Karnataka, India",
    href: "https://maps.google.com/?q=Gokulam,Mysore,Karnataka,India",
  },
];

const testimonials = [
  {
    name: "Rajesh Kumar",
    restaurant: "Spice Garden, Bangalore",
    text: "Zen Menu transformed how we serve our customers. Setup took 5 minutes and our diners love the digital menu!",
    rating: 5,
  },
  {
    name: "Priya Nair",
    restaurant: "Kerala Kitchen, Kochi",
    text: "We saved thousands on printing costs and can update our menu in real-time. Highly recommended!",
    rating: 5,
  },
  {
    name: "Amit Sharma",
    restaurant: "The Urban Plate, Mumbai",
    text: "The QR code system is seamless. Our customers scan and order without any hassle. Great product!",
    rating: 5,
  },
];

const faqs = [
  {
    q: "How quickly can I set up Zen Menu?",
    a: "You can have your digital menu live in under 10 minutes. Just sign up, add your items, generate QR codes, and you're ready!",
  },
  {
    q: "Is there a free plan available?",
    a: "Yes! Our free plan lets you create 1 restaurant with up to 20 menu items and 5 QR codes — no credit card required.",
  },
  {
    q: "Can I update my menu in real-time?",
    a: "Absolutely. Any changes you make are reflected instantly on your digital menu. No reprinting needed.",
  },
  {
    q: "Do my customers need to install an app?",
    a: "No! Customers simply scan the QR code with their phone camera and the menu opens in their browser — no app required.",
  },
  {
    q: "What payment methods do you accept?",
    a: "We accept all major payment methods through Razorpay — UPI, credit/debit cards, net banking, and wallets.",
  },
  {
    q: "How do I get support?",
    a: "Reach us via WhatsApp for the fastest response, or email us at hello@zenqrmenu.com. We typically respond within a few hours.",
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] as const },
  }),
};

const ContactPage = () => {
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    restaurant: "",
    message: "",
  });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }
    setSending(true);
    try {
      // Send via WhatsApp as fallback / primary
      const text = `*New Contact from Zen Menu Website*\n\n*Name:* ${form.name}\n*Email:* ${form.email}\n*Phone:* ${form.phone || "N/A"}\n*Restaurant:* ${form.restaurant || "N/A"}\n*Message:* ${form.message}`;
      window.open(`${WHATSAPP_LINK}?text=${encodeURIComponent(text)}`, "_blank");
      setSent(true);
      toast.success("Opening WhatsApp to send your message!");
    } catch {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Hero */}
      <section className="gradient-hero">
        <div className="container py-16 lg:py-24 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-2xl mx-auto"
          >
            <h1 className="text-4xl md:text-5xl font-extrabold font-heading leading-tight tracking-tight">
              Let's <span className="text-gradient">Get in Touch</span>
            </h1>
            <p className="mt-4 text-lg text-muted-foreground">
              Have questions? Want a demo? We'd love to hear from you. Reach out and we'll respond within hours.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 justify-center">
              <a href={`${WHATSAPP_LINK}?text=${encodeURIComponent("Hi, I'd like a free demo of Zen Menu!")}`} target="_blank" rel="noopener noreferrer">
                <Button variant="hero" size="lg" className="text-base px-8">
                  <MessageCircle className="mr-2 h-5 w-5" /> Chat on WhatsApp
                </Button>
              </a>
              <a href="#contact-form">
                <Button variant="hero-outline" size="lg" className="text-base px-8">
                  Send a Message <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Contact Methods */}
      <section className="py-16 lg:py-20">
        <div className="container">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {contactMethods.map((method, i) => (
              <motion.a
                key={method.title}
                href={method.href}
                target="_blank"
                rel="noopener noreferrer"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-30px" }}
                variants={fadeUp}
                custom={i}
                className="group rounded-xl border bg-card p-6 shadow-card hover:shadow-elevated transition-all hover:border-primary/30 cursor-pointer"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent mb-4 group-hover:bg-primary/10 transition-colors">
                  <method.icon className="h-6 w-6 text-accent-foreground" />
                </div>
                <h3 className="font-semibold text-lg mb-1">{method.title}</h3>
                <p className="text-primary font-medium text-sm">{method.detail}</p>
                <p className="text-xs text-muted-foreground mt-1">{method.description}</p>
              </motion.a>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Form + Demo CTA */}
      <section id="contact-form" className="py-16 lg:py-20 bg-muted/50">
        <div className="container">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            {/* Form */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={0}
            >
              <h2 className="text-3xl font-bold font-heading mb-2">
                Send Us a <span className="text-gradient">Message</span>
              </h2>
              <p className="text-muted-foreground mb-8">
                Fill in the form and we'll get back to you within 24 hours.
              </p>

              {sent ? (
                <div className="rounded-xl border bg-card p-8 text-center">
                  <CheckCircle2 className="h-16 w-16 text-primary mx-auto mb-4" />
                  <h3 className="text-xl font-bold mb-2">Message Sent!</h3>
                  <p className="text-muted-foreground mb-4">
                    Thank you for reaching out. We'll get back to you shortly.
                  </p>
                  <Button variant="hero-outline" onClick={() => setSent(false)}>
                    Send Another Message
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5 rounded-xl border bg-card p-6 md:p-8 shadow-card">
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Name *</Label>
                      <Input id="name" name="name" placeholder="Your name" value={form.name} onChange={handleChange} required maxLength={100} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">Email *</Label>
                      <Input id="email" name="email" type="email" placeholder="you@example.com" value={form.email} onChange={handleChange} required maxLength={255} />
                    </div>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="phone">Phone (optional)</Label>
                      <Input id="phone" name="phone" type="tel" placeholder="+91-XXXXXXXXXX" value={form.phone} onChange={handleChange} maxLength={20} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="restaurant">Restaurant Name</Label>
                      <Input id="restaurant" name="restaurant" placeholder="Your restaurant" value={form.restaurant} onChange={handleChange} maxLength={100} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="message">Message / Requirement *</Label>
                    <Textarea id="message" name="message" placeholder="Tell us what you're looking for..." value={form.message} onChange={handleChange} required maxLength={1000} rows={4} />
                  </div>
                  <Button type="submit" variant="hero" className="w-full" disabled={sending}>
                    {sending ? "Sending..." : <><Send className="mr-2 h-4 w-4" /> Send Message</>}
                  </Button>
                </form>
              )}
            </motion.div>

            {/* Demo CTA */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={1}
              className="space-y-8"
            >
              <div className="rounded-xl border bg-card p-8 shadow-card">
                <h3 className="text-2xl font-bold font-heading mb-3">
                  Book a <span className="text-gradient">Free Demo</span>
                </h3>
                <p className="text-muted-foreground mb-6">
                  See Zen Menu in action! We'll walk you through the platform and show you how easy it is to digitize your restaurant menu.
                </p>
                <ul className="space-y-3 mb-6">
                  {["Personalized walkthrough", "Setup assistance included", "No commitment required", "Takes just 15 minutes"].map((item) => (
                    <li key={item} className="flex items-center gap-3 text-sm">
                      <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <a href={`${WHATSAPP_LINK}?text=${encodeURIComponent("Hi! I'd like to book a free demo of Zen Menu for my restaurant.")}`} target="_blank" rel="noopener noreferrer">
                  <Button variant="hero" className="w-full" size="lg">
                    <MessageCircle className="mr-2 h-5 w-5" /> Book Free Demo on WhatsApp
                  </Button>
                </a>
              </div>

              <div className="rounded-xl border bg-card p-8 shadow-card">
                <h3 className="text-lg font-bold mb-4">Why Restaurants Choose Us</h3>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { icon: Users, label: "100+ Restaurants", sub: "Trust Zen Menu" },
                    { icon: Clock, label: "< 10 Minutes", sub: "To go live" },
                    { icon: Star, label: "4.9/5 Rating", sub: "Customer satisfaction" },
                    { icon: CheckCircle2, label: "99.9% Uptime", sub: "Always available" },
                  ].map((stat) => (
                    <div key={stat.label} className="text-center p-3">
                      <stat.icon className="h-6 w-6 text-primary mx-auto mb-2" />
                      <p className="font-bold text-sm">{stat.label}</p>
                      <p className="text-xs text-muted-foreground">{stat.sub}</p>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-16 lg:py-20">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
            className="text-center max-w-2xl mx-auto mb-12"
          >
            <h2 className="text-3xl md:text-4xl font-bold font-heading">
              Trusted by <span className="text-gradient">Restaurant Owners</span>
            </h2>
            <p className="mt-4 text-muted-foreground text-lg">
              See what our customers have to say about Zen Menu.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t, i) => (
              <motion.div
                key={t.name}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i}
                className="rounded-xl border bg-card p-6 shadow-card"
              >
                <div className="flex gap-1 mb-3">
                  {Array.from({ length: t.rating }).map((_, j) => (
                    <Star key={j} className="h-4 w-4 fill-primary text-primary" />
                  ))}
                </div>
                <p className="text-sm text-muted-foreground mb-4 italic">"{t.text}"</p>
                <div>
                  <p className="font-semibold text-sm">{t.name}</p>
                  <p className="text-xs text-muted-foreground">{t.restaurant}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 lg:py-20 bg-muted/50">
        <div className="container max-w-3xl">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
            className="text-center mb-12"
          >
            <h2 className="text-3xl md:text-4xl font-bold font-heading">
              Frequently Asked <span className="text-gradient">Questions</span>
            </h2>
          </motion.div>

          <div className="space-y-4">
            {faqs.map((faq, i) => (
              <motion.details
                key={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i}
                className="group rounded-xl border bg-card p-5 shadow-card cursor-pointer"
              >
                <summary className="font-semibold text-sm list-none flex items-center justify-between">
                  {faq.q}
                  <span className="text-primary ml-2 group-open:rotate-45 transition-transform text-lg">+</span>
                </summary>
                <p className="mt-3 text-sm text-muted-foreground">{faq.a}</p>
              </motion.details>
            ))}
          </div>
        </div>
      </section>

      {/* Map */}
      <section className="py-16 lg:py-20">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
            className="text-center mb-8"
          >
            <h2 className="text-3xl font-bold font-heading">
              Find <span className="text-gradient">Us</span>
            </h2>
            <p className="mt-2 text-muted-foreground">Gokulam, Mysore, Karnataka, India</p>
          </motion.div>
          <div className="rounded-xl overflow-hidden shadow-card border">
            <iframe
              title="Zen Menu Office Location"
              src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d15601.0!2d76.6394!3d12.3252!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3baf70381d572ef9%3A0x2b89b12e50a49b10!2sGokulam%2C%20Mysuru%2C%20Karnataka!5e0!3m2!1sen!2sin!4v1700000000000!5m2!1sen!2sin"
              width="100%"
              height="350"
              style={{ border: 0 }}
              allowFullScreen
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          </div>
        </div>
      </section>

      {/* WhatsApp Floating CTA */}
      <a
        href={`${WHATSAPP_LINK}?text=${encodeURIComponent("Hi! I'm interested in Zen Menu.")}`}
        target="_blank"
        rel="noopener noreferrer"
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-[#25D366] text-white shadow-lg hover:scale-110 transition-transform"
        aria-label="Chat on WhatsApp"
      >
        <MessageCircle className="h-7 w-7" />
      </a>

      <Footer />
    </div>
  );
};

export default ContactPage;
