import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CheckCircle2, ArrowRight } from "lucide-react";
import Navbar from "@/components/Navbar";

const PaymentSuccessPage = () => (
  <div className="min-h-screen flex flex-col">
    <Navbar />
    <main className="flex-1 flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <Card className="max-w-md w-full p-10 text-center shadow-elevated">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100 mb-6">
            <CheckCircle2 className="h-9 w-9 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold font-heading mb-2">Payment Successful!</h1>
          <p className="text-muted-foreground mb-8">
            Your subscription is now active. Start building your digital menu and generating QR codes.
          </p>
          <div className="flex flex-col gap-3">
            <Link to="/dashboard">
              <Button variant="hero" className="w-full">
                Go to Dashboard <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link to="/">
              <Button variant="ghost" className="w-full">Back to Home</Button>
            </Link>
          </div>
        </Card>
      </motion.div>
    </main>
  </div>
);

export default PaymentSuccessPage;
