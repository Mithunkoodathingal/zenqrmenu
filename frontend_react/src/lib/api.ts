// API configuration — update BASE_URL to your Django backend
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.zenqrmenu.com";

import { authHeaders, authFetch, getToken } from "./auth";

export interface Plan {
  id: number | string;
  name: string;
  price: number;
  period?: string;
  duration_days?: number;
  table_limit?: number;
  features: string[] | string;
  popular?: boolean;
}

// Normalize backend plan data
export function normalizePlan(plan: Plan): Plan & { features: string[] } {
  const features = typeof plan.features === "string"
    ? plan.features.split(",").map((f) => f.trim()).filter(Boolean)
    : plan.features;
  return {
    ...plan,
    features,
    period: plan.period || (plan.duration_days === 30 ? "/month" : plan.duration_days ? `/${plan.duration_days} days` : "/month"),
    popular: plan.popular ?? plan.name === "Standard",
  };
}

export interface RazorpayOrder {
  order_id: string;
  amount: number;
  key: string;
  razorpay_key?: string;
  currency?: string;
  free?: boolean;
}

export interface PaymentVerification {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface AuthUser {
  username: string;
  email: string;
}

export interface LoginResponse {
  success?: boolean;
  message?: string;
  error?: string;
  email?: string;
  user?: AuthUser;
  token?: string;
  access_token?: string;
  access?: string;
  jwt?: string;
  refresh?: string;
}

export interface CurrentUserResponse {
  authenticated: boolean;
  user?: AuthUser;
}

// Fetch subscription plans
export async function fetchPlans(): Promise<Plan[]> {
  const res = await fetch(`${BASE_URL}/subscription/api/plans/`, {
    credentials: "include",
    headers: { "Accept": "application/json", ...authHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch plans");
  const data = await res.json();
  // Backend may wrap plans in { plans: [...] }
  return Array.isArray(data) ? data : (data.plans ?? []);
}

// Create subscription + Razorpay order
export async function createSubscription(planId: string | number): Promise<RazorpayOrder> {
  if (!getToken()) {
    throw new Error("LOGIN_REQUIRED");
  }
  const res = await authFetch(`${BASE_URL}/subscription/api/create/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ plan_id: planId }),
  });
  if (res.status === 401 || res.status === 403) {
    throw new Error("LOGIN_REQUIRED");
  }
  const contentType = res.headers.get("content-type") || "";
  if (!res.ok) {
    let detail = "";
    try {
      if (contentType.includes("application/json")) {
        const body = await res.json();
        detail = body.error || body.message || body.detail || "";
      } else {
        detail = await res.text();
      }
    } catch {
      // ignore
    }
    throw new Error(detail ? `Subscription failed: ${detail}` : `Subscription failed (${res.status})`);
  }
  if (!contentType.includes("application/json")) {
    throw new Error("Subscription failed: invalid server response");
  }
  return res.json();
}

// Verify payment after Razorpay checkout
export async function verifyPayment(data: PaymentVerification): Promise<{ success: boolean; message?: string }> {
  const res = await authFetch(`${BASE_URL}/subscription/api/verify/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Payment verification failed");
  return res.json();
}

// ─── Auth ───

export async function apiResendVerification(email: string): Promise<{ success?: boolean; message?: string; error?: string }> {
  const res = await fetch(`${BASE_URL}/api/auth/resend-verification/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  return res.json();
}

export async function apiPasswordReset(email: string): Promise<{ success?: boolean; message?: string; error?: string }> {
  const res = await fetch(`${BASE_URL}/api/auth/password/reset/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  return res.json();
}

export async function apiPasswordResetConfirm(data: {
  uid: string;
  token: string;
  new_password1: string;
  new_password2: string;
}): Promise<{ success?: boolean; message?: string; error?: string; errors?: Record<string, string[]> }> {
  const res = await fetch(`${BASE_URL}/api/auth/password/reset/confirm/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function apiRegister(data: {
  username: string;
  email: string;
  password1: string;
  password2: string;
}): Promise<{ success: boolean; message?: string; errors?: Record<string, string[]> }> {
  const res = await fetch(`${BASE_URL}/api/auth/register/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function apiLogin(data: {
  username: string;
  password: string;
}): Promise<LoginResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/login/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error("Invalid login response");
  }
  const json = await res.json();
  // Pass through error fields from 400/403 responses
  if (!res.ok) {
    return { error: json.error || json.message || "Login failed", email: json.email };
  }
  return json;
}

export async function apiLogout(): Promise<{ success: boolean }> {
  const res = await fetch(`${BASE_URL}/api/auth/logout/`, {
    method: "POST",
    credentials: "include",
  });
  return res.json();
}

export async function apiGetUser(): Promise<CurrentUserResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/user/`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  });

  if (!res.ok) {
    return { authenticated: false };
  }

  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return { authenticated: false };
  }

  return res.json();
}
