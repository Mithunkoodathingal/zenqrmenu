import type { RazorpayOrder } from "./api";

declare global {
  interface Window {
    Razorpay: new (options: Record<string, unknown>) => {
      open: () => void;
      on: (event: string, callback: () => void) => void;
    };
  }
}

// Load Razorpay script dynamically
export function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

interface RazorpayCallbacks {
  onSuccess: (response: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) => void;
  onFailure: (error: unknown) => void;
}

export function openRazorpayCheckout(
  order: RazorpayOrder,
  callbacks: RazorpayCallbacks,
  prefill?: { name?: string; email?: string; contact?: string }
) {
  const options = {
    key: order.key || order.razorpay_key,
    amount: order.amount,
    currency: order.currency || "INR",
    name: "Zen Menu",
    description: "Subscription Payment",
    order_id: order.order_id,
    handler: callbacks.onSuccess,
    prefill: prefill || {},
    theme: { color: "#f97316" },
    modal: {
      ondismiss: () => callbacks.onFailure("Payment cancelled"),
    },
  };

  const rzp = new window.Razorpay(options);
  rzp.open();
}
