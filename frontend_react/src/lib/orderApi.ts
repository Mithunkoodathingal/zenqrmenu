import { authHeaders } from "./auth";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.zenqrmenu.com";

// ─── Types ───

export interface OrderItemPayload {
  food_item_id: number;
  quantity: number;
  selected_addons_ids?: number[];
}

export interface CreateOrderPayload {
  restaurant?: number;
  table: number | string;
  customer_name?: string;
  customer_phone?: string;
  items: OrderItemPayload[];
}

export interface OrderItem {
  id?: number;
  menu_item_id?: number;
  food_item_name?: string;
  name: string;
  quantity: number;
  price: number;
  selected_addons?: unknown[];
}

export interface Order {
  id: number;
  table: number;
  table_number: string;
  customer_name?: string;
  customer_phone?: string;
  total_price: number;
  status: "pending" | "confirmed" | "preparing" | "ready" | "completed" | "cancelled";
  created_at: string;
  items: OrderItem[];
}

// Normalize raw backend order to our Order type
function normalizeOrder(raw: any, fallbackOrderId?: number): Order {
  const orderItems = (raw.order_items || raw.items || []).map((item: any) => ({
    id: item.id,
    menu_item_id: item.menu_item_id || item.food_item_id,
    name: item.food_item_name || item.name || "Unknown Item",
    quantity: item.quantity || 1,
    price: parseFloat(item.price || item.unit_price || "0"),
    selected_addons: item.selected_addons || [],
  }));

  return {
    id: raw.id ?? fallbackOrderId ?? 0,
    table: Number(raw.table ?? 0),
    table_number: String(raw.table_number || raw.table || ""),
    customer_name: raw.customer_name || undefined,
    customer_phone: raw.customer_phone || undefined,
    total_price: parseFloat(raw.total_price_cached || raw.total_price || raw.total || "0"),
    status: raw.status || "pending",
    created_at: raw.created_at || new Date().toISOString(),
    items: orderItems,
  };
}

// ─── Public: Place order (no auth) ───

export async function createOrder(payload: CreateOrderPayload): Promise<Order | null> {
  const res = await fetch(`${BASE_URL}/menu/api/orders/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });

  const rawBody = await res.text().catch(() => "");

  if (!res.ok) {
    console.error("[createOrder] failed:", res.status, rawBody);
    let message = `Failed to place order (${res.status})`;
    try {
      const parsed = rawBody ? JSON.parse(rawBody) : null;
      message = parsed?.detail || parsed?.message || parsed?.error || message;
    } catch {
      if (rawBody) message = rawBody;
    }
    throw new Error(message);
  }

  if (!rawBody) return null;

  try {
    const parsed = JSON.parse(rawBody);
    return normalizeOrder(parsed);
  } catch {
    return null;
  }
}

// ─── Public: Fetch order status by ID (no auth) ───

export async function fetchPublicOrder(orderId: number): Promise<Order | null> {
  try {
    const url = `${BASE_URL}/menu/api/orders/${orderId}/public/?_=${Date.now()}`;
    const res = await fetch(url, {
      headers: {
        Accept: "application/json",
        "Cache-Control": "no-cache",
        Pragma: "no-cache",
      },
      cache: "no-store",
    });

    const rawBody = await res.text().catch(() => "");
    console.log("[fetchPublicOrder] response:", { orderId, status: res.status, body: rawBody });

    if (!res.ok) {
      console.warn("[fetchPublicOrder] failed:", orderId, res.status, rawBody);
      return null;
    }

    if (!rawBody) return null;

    const data = JSON.parse(rawBody);
    return normalizeOrder(data, orderId);
  } catch (error) {
    console.warn("[fetchPublicOrder] error:", orderId, error);
    return null;
  }
}

// ─── Public: Fetch active orders for a table (no auth) ───

export async function fetchTableOrders(tableId: number | string): Promise<Order[]> {
  try {
    const res = await fetch(`${BASE_URL}/menu/api/table/${tableId}/orders/`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data.map(normalizeOrder) : [];
  } catch {
    return [];
  }
}

// ─── Dashboard: List orders (auth required) ───

export async function fetchOrders(restaurantId?: number): Promise<Order[]> {
  const params = restaurantId ? `?restaurant_id=${restaurantId}` : "";
  const res = await fetch(`${BASE_URL}/menu/api/orders/${params}`, {
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error("Failed to fetch orders");
  const data = await res.json();
  return Array.isArray(data) ? data.map(normalizeOrder) : [];
}

// ─── Dashboard: Delete order (auth required) ───

export async function deleteOrder(orderId: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/menu/api/orders/${orderId}/`, {
    method: "DELETE",
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to delete order");
}

// ─── Dashboard: Update order status (auth required) ───

export async function updateOrderStatus(
  orderId: number,
  status: Order["status"]
): Promise<Order> {
  const res = await fetch(`${BASE_URL}/menu/api/orders/${orderId}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...authHeaders(),
    },
    credentials: "include",
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error("Failed to update order status");
  return res.json();
}

