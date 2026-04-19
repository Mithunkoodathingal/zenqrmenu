import { authHeaders } from "./auth";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://www.zenqrmenu.com";

// ─── Types ───

export interface RestaurantProfile {
  id: number;
  name: string;
  cuisine_type?: string;
  address?: string;
  phone?: string;
  about?: string;
  logo?: string | null;
  cover_image?: string | null;
  slug?: string;
}

export interface PublicMenuData {
  restaurant: {
    id?: number;
    name: string;
    address?: string;
    logo?: string | null;
    cover_image?: string | null;
  };
  categories: { id: number; name: string }[];
  items: {
    id: number;
    name: string;
    price: number;
    description: string;
    category: number;
    is_available: boolean;
    image?: string | null;
    is_veg?: boolean;
  }[];
}

type RawCategory = {
  id?: number | string;
  name?: string;
};

type RawMenuItem = {
  id?: number | string;
  name?: string;
  price?: number | string;
  description?: string;
  category?: number | string | RawCategory | null;
  category_id?: number | string | null;
  is_available?: boolean;
  available?: boolean;
  is_paused?: boolean;
  image?: string | null;
  image_url?: string | null;
  is_veg?: boolean;
  veg?: boolean;
};

function toNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function normalizeCategory(category: RawCategory | null | undefined) {
  const id = toNumber(category?.id);
  const name = category?.name?.trim();
  if (!id || !name) return null;
  return { id, name };
}

function normalizeItem(item: RawMenuItem) {
  const id = toNumber(item.id);
  const name = item.name?.trim();
  const price = toNumber(item.price) ?? 0;

  const categoryId =
    toNumber(item.category_id) ??
    toNumber(typeof item.category === "object" && item.category ? item.category.id : item.category);

  if (!id || !name || !categoryId) return null;

  return {
    id,
    name,
    price,
    description: item.description?.trim() || "",
    category: categoryId,
    is_available:
      typeof item.is_paused === "boolean"
        ? !item.is_paused
        : item.is_available ?? item.available ?? true,
    image: item.image ?? item.image_url ?? null,
    is_veg: item.is_veg ?? item.veg,
  };
}

function normalizePublicMenuData(data: any): PublicMenuData {
  const restaurantSource = data?.restaurant ?? data?.profile ?? data?.restaurant_profile ?? data ?? {};
  const rawItems =
    data?.items ??
    data?.menu_items ??
    data?.menuItems ??
    data?.products ??
    data?.results?.items ??
    [];

  const items = Array.isArray(rawItems)
    ? rawItems
        .map((item) => normalizeItem(item as RawMenuItem))
        .filter((item): item is NonNullable<typeof item> => item !== null)
    : [];

  const rawCategories =
    data?.categories ??
    data?.category_list ??
    data?.results?.categories ??
    [];

  const categoriesFromResponse = Array.isArray(rawCategories)
    ? rawCategories
        .map((category) => normalizeCategory(category as RawCategory))
        .filter((category): category is NonNullable<typeof category> => category !== null)
    : [];

  const inferredCategories = items.reduce<PublicMenuData["categories"]>((acc, item) => {
    const rawCategory = Array.isArray(rawItems)
      ? (rawItems.find((entry: RawMenuItem) => toNumber(entry.id) === item.id)?.category as RawCategory | undefined)
      : undefined;

    const normalized =
      typeof rawCategory === "object" && rawCategory ? normalizeCategory(rawCategory) : null;

    if (normalized && !acc.some((category) => category.id === normalized.id)) {
      acc.push(normalized);
    }

    return acc;
  }, []);

  return {
    restaurant: {
      id: toNumber(restaurantSource.id),
      name: restaurantSource.name?.trim() || "Restaurant",
      address: restaurantSource.address?.trim() || "",
      logo: restaurantSource.logo ?? null,
      cover_image: restaurantSource.cover_image ?? restaurantSource.cover_photo ?? null,
    },
    categories: categoriesFromResponse.length > 0 ? categoriesFromResponse : inferredCategories,
    items,
  };
}

export function resolveImageUrl(image?: string | null): string | undefined {
  if (!image) return undefined;
  if (/^https?:\/\//i.test(image)) return image;
  return `${BASE_URL}${image.startsWith("/") ? "" : "/"}${image}`;
}

// ─── Restaurant Profile (auth required) ───

export async function fetchRestaurantProfile(): Promise<RestaurantProfile> {
  const res = await fetch(`${BASE_URL}/menu/api/restaurant/`, {
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error("Failed to fetch restaurant profile");
  return res.json();
}

export async function updateRestaurantProfile(
  data: Record<string, unknown>
): Promise<RestaurantProfile> {
  const headers: Record<string, string> = { Accept: "application/json", ...authHeaders() };
  const hasFile = Object.values(data).some((v) => v instanceof File);

  let body: BodyInit;
  if (hasFile) {
    const formData = new FormData();
    Object.entries(data).forEach(([key, value]) => {
      if (value === undefined) return;
      if (value === null) { formData.append(key, ""); return; }
      if (value instanceof File) { formData.append(key, value); return; }
      formData.append(key, String(value));
    });
    body = formData;
  } else {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(data);
  }

  const res = await fetch(`${BASE_URL}/menu/api/restaurant/`, {
    method: "PATCH",
    headers,
    credentials: "include",
    body,
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error("Failed to update restaurant profile");
  return res.json();
}

// ─── Tables (auth required) ───

export interface RestaurantTable {
  id: number;
  table_number: number | string;
  qr_code?: string;
}

export async function fetchTables(): Promise<RestaurantTable[]> {
  const res = await fetch(`${BASE_URL}/menu/api/tables/`, {
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error("Failed to fetch tables");
  return res.json();
}

export async function createTable(tableNumber: number): Promise<RestaurantTable> {
  const res = await fetch(`${BASE_URL}/menu/api/tables/`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ table_number: tableNumber }),
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) {
    let msg = "Failed to create table";
    try {
      const body = await res.json();
      msg = body?.error || body?.detail || body?.message || JSON.stringify(body);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function deleteTable(tableId: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/menu/api/tables/${tableId}/`, {
    method: "DELETE",
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (res.status === 204 || res.ok) return;
  let msg = "Failed to delete table";
  try {
    const body = await res.json();
    msg = body?.error || body?.detail || body?.message || msg;
  } catch {}
  throw new Error(msg);
}

// ─── Public Menu (no auth) ───

export async function fetchPublicMenu(tableId: string): Promise<PublicMenuData> {
  const res = await fetch(`${BASE_URL}/menu/api/table/${tableId}/`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error("Menu not found");
  const data = await res.json();
  console.log("[fetchPublicMenu] raw API response:", JSON.stringify(data).substring(0, 2000));
  return normalizePublicMenuData(data);
}
