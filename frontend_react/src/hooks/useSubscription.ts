import { useQuery } from "@tanstack/react-query";
import { fetchSubscriptionStatus, type SubscriptionStatus } from "@/lib/subscriptionApi";
import { getStoredUser } from "@/lib/auth";

const SUBSCRIPTION_STORAGE_KEY = "zen_subscription_status";
const UNLIMITED_LIMIT = Number.MAX_SAFE_INTEGER;

type StoredSubscriptionStatus = SubscriptionStatus & {
  _ownerKey?: string;
};

type SubscriptionPlanSnapshot = {
  name: string;
  table_limit?: number;
  features?: string[] | string;
};

function normalizePlanName(plan?: string | null) {
  return plan?.trim().toLowerCase() ?? "";
}

function getSubscriptionOwnerKey() {
  const user = getStoredUser();
  return user?.email || user?.username || "";
}

function hasUnlimitedItems(features?: string[] | string) {
  const featureList = Array.isArray(features)
    ? features
    : typeof features === "string"
      ? features.split(",")
      : [];

  return featureList.some((feature) => /unlimited.*(item|items|categories)/i.test(feature));
}

export function persistSubscriptionStatus(status: SubscriptionStatus) {
  const ownerKey = getSubscriptionOwnerKey();

  if (!ownerKey) {
    localStorage.removeItem(SUBSCRIPTION_STORAGE_KEY);
    return;
  }

  localStorage.setItem(
    SUBSCRIPTION_STORAGE_KEY,
    JSON.stringify({ ...status, _ownerKey: ownerKey } satisfies StoredSubscriptionStatus),
  );
}

export function clearStoredSubscriptionStatus() {
  localStorage.removeItem(SUBSCRIPTION_STORAGE_KEY);
}

export function persistPlanSubscription(plan: SubscriptionPlanSnapshot) {
  const normalizedPlan = normalizePlanName(plan.name);
  const snapshot: SubscriptionStatus = {
    plan: normalizedPlan,
    table_limit: plan.table_limit ?? 0,
    menu_item_limit: hasUnlimitedItems(plan.features) ? UNLIMITED_LIMIT : 0,
    is_active: normalizedPlan !== "free",
  };

  persistSubscriptionStatus(snapshot);
}

export function getStoredSubscriptionStatus(): SubscriptionStatus | undefined {
  try {
    const raw = localStorage.getItem(SUBSCRIPTION_STORAGE_KEY);
    if (!raw) return undefined;

    const parsed = JSON.parse(raw) as StoredSubscriptionStatus;
    const ownerKey = getSubscriptionOwnerKey();

    if (!ownerKey || !parsed._ownerKey || parsed._ownerKey !== ownerKey) {
      return undefined;
    }

    const { _ownerKey, ...status } = parsed;
    return status;
  } catch {
    return undefined;
  }
}

export function isUnlimitedLimit(limit: number) {
  return !Number.isFinite(limit) || limit >= UNLIMITED_LIMIT;
}

export function isEffectivelyUnlimited(limit: number) {
  return limit === 0 || isUnlimitedLimit(limit);
}

export function hasActivePaidSubscription(status?: SubscriptionStatus) {
  if (!status) return false;

  const normalizedPlan = normalizePlanName(status.plan);
  if (!status.is_active || !normalizedPlan || normalizedPlan === "free") return false;
  if ((status.error || "").toLowerCase().includes("no subscription")) return false;

  return status.table_limit > 0 || status.menu_item_limit > 0 || isUnlimitedLimit(status.table_limit) || isUnlimitedLimit(status.menu_item_limit);
}

export function useSubscription() {
  return useQuery<SubscriptionStatus>({
    queryKey: ["subscriptionStatus"],
    queryFn: async () => {
      try {
        const status = await fetchSubscriptionStatus();
        persistSubscriptionStatus(status);
        return status;
      } catch (error) {
        clearStoredSubscriptionStatus();
        throw error;
      }
    },
    initialData: getStoredSubscriptionStatus,
    retry: (count, error: any) => error.message !== "LOGIN_REQUIRED" && count < 2,
    staleTime: 60_000, // cache for 1 min
  });
}

export function useCanAddTable(currentTableCount: number) {
  const { data, isError } = useSubscription();
  if (isError || !data) return { allowed: true, limit: UNLIMITED_LIMIT, reason: "" };
  if (!hasActivePaidSubscription(data)) return { allowed: false, limit: 0, reason: data.error || "No active subscription. Please subscribe to a plan first." };
  if (!isUnlimitedLimit(data.table_limit) && currentTableCount >= data.table_limit) {
    return { allowed: false, limit: data.table_limit, reason: `You've reached your limit of ${data.table_limit} tables. Upgrade to add more.` };
  }
  return { allowed: true, limit: data.table_limit, reason: "" };
}

export function useCanAddMenuItem(_currentItemCount: number) {
  const { data, isError } = useSubscription();
  if (isError || !data) return { allowed: true, limit: UNLIMITED_LIMIT, reason: "" };
  if (!hasActivePaidSubscription(data)) return { allowed: false, limit: 0, reason: data.error || "No active subscription. Please subscribe to a plan first." };
  return { allowed: true, limit: UNLIMITED_LIMIT, reason: "" };
}
