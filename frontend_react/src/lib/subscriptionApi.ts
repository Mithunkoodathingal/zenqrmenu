import { authHeaders } from "./auth";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.zenqrmenu.com";

export interface SubscriptionStatus {
  plan: string;
  menu_item_limit: number;
  table_limit: number;
  is_active: boolean;
  error?: string;
}

export async function fetchSubscriptionStatus(): Promise<SubscriptionStatus> {
  const res = await fetch(`${BASE_URL}/subscription/api/subscription/`, {
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error("Failed to fetch subscription status");
  return res.json();
}
