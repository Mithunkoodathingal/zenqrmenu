import { authHeaders } from "./auth";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://www.zenqrmenu.com";

// ─── Types ───

export interface ApiCategory {
  id: number;
  name: string;
}

export interface ApiMenuItem {
  id: number;
  name: string;
  price: number;
  description: string;
  category: number;
  is_available: boolean;
  image?: string | null;
}

type RawApiMenuItem = {
  id: number;
  name: string;
  price: number;
  description: string;
  category: number | { id?: number };
  is_available?: boolean;
  available?: boolean;
  is_paused?: boolean;
  image?: string | null;
};

export type MenuItemInput = Omit<ApiMenuItem, "id" | "image" | "is_available"> & {
  is_available?: boolean;
  is_paused?: boolean;
  image?: string | File | null;
};

function normalizeAvailability(item: Pick<RawApiMenuItem, "is_available" | "available" | "is_paused">) {
  if (typeof item.is_paused === "boolean") return !item.is_paused;
  return item.is_available ?? item.available ?? true;
}

function normalizeMenuItem(item: RawApiMenuItem): ApiMenuItem {
  return {
    id: item.id,
    name: item.name,
    price: Number(item.price),
    description: item.description ?? "",
    category: typeof item.category === "object" ? Number(item.category?.id) : Number(item.category),
    is_available: normalizeAvailability(item),
    image: item.image ?? null,
  };
}

export function resolveMenuImageUrl(image?: string | null): string | undefined {
  if (!image) return undefined;
  if (/^https?:\/\//i.test(image)) return image;
  return `${BASE_URL}${image.startsWith("/") ? "" : "/"}${image}`;
}

async function getErrorMessage(res: Response, fallback: string): Promise<string> {
  const contentType = res.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const data = await res.json().catch(() => null);
    if (!data) return fallback;
    if (typeof data.message === "string") return data.message;
    if (typeof data.detail === "string") return data.detail;
    if (typeof data.error === "string") return data.error;

    const fieldError = Object.entries(data).find(([, value]) => Array.isArray(value) && value.length);
    if (fieldError) {
      const [field, messages] = fieldError;
      return `${field}: ${(messages as string[]).join(", ")}`;
    }
  }

  const text = await res.text().catch(() => "");
  return text.trim() || fallback;
}

function buildMenuItemBody(data: Partial<MenuItemInput>) {
  const normalizedData: Partial<MenuItemInput> = { ...data };

  if (typeof normalizedData.is_paused === "boolean" && typeof normalizedData.is_available !== "boolean") {
    normalizedData.is_available = !normalizedData.is_paused;
  }

  if (typeof normalizedData.is_available === "boolean" && typeof normalizedData.is_paused !== "boolean") {
    normalizedData.is_paused = !normalizedData.is_available;
  }

  const headers = { Accept: "application/json", ...authHeaders() };
  const hasFile = normalizedData.image instanceof File;

  if (!hasFile) {
    return {
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(normalizedData),
    };
  }

  const formData = new FormData();
  Object.entries(normalizedData).forEach(([key, value]) => {
    if (value === undefined) return;
    if (value === null) {
      formData.append(key, "");
      return;
    }
    if (value instanceof File) {
      formData.append(key, value);
      return;
    }
    if (typeof value === "boolean") {
      formData.append(key, value ? "true" : "false");
      return;
    }
    formData.append(key, String(value));
  });

  return { headers, body: formData };
}

// ─── Categories ───

export async function fetchCategories(): Promise<ApiCategory[]> {
  const res = await fetch(`${BASE_URL}/menu/api/categories/`, {
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to fetch categories"));
  return res.json();
}

export async function createCategory(name: string): Promise<ApiCategory> {
  const res = await fetch(`${BASE_URL}/menu/api/categories/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify({ name }),
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to create category"));
  return res.json();
}

export async function updateCategory(id: number, data: Partial<ApiCategory>): Promise<ApiCategory> {
  const res = await fetch(`${BASE_URL}/menu/api/categories/${id}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(data),
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to update category"));
  return res.json();
}

export async function deleteCategory(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/menu/api/categories/${id}/`, {
    method: "DELETE",
    headers: { ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to delete category"));
}

// ─── Menu Items ───

export async function fetchMenuItems(): Promise<ApiMenuItem[]> {
  const res = await fetch(`${BASE_URL}/menu/api/items/`, {
    headers: { Accept: "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to fetch menu items"));
  const data = await res.json();
  return Array.isArray(data) ? data.map((item) => normalizeMenuItem(item as RawApiMenuItem)) : [];
}

export async function createMenuItem(data: MenuItemInput): Promise<ApiMenuItem> {
  const payload = buildMenuItemBody(data);
  const res = await fetch(`${BASE_URL}/menu/api/items/`, {
    method: "POST",
    headers: payload.headers,
    credentials: "include",
    body: payload.body,
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to create menu item"));
  return normalizeMenuItem((await res.json()) as RawApiMenuItem);
}

export async function updateMenuItem(id: number, data: Partial<MenuItemInput>): Promise<ApiMenuItem> {
  const payload = buildMenuItemBody(data);
  const res = await fetch(`${BASE_URL}/menu/api/items/${id}/`, {
    method: "PATCH",
    headers: payload.headers,
    credentials: "include",
    body: payload.body,
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to update menu item"));
  return normalizeMenuItem((await res.json()) as RawApiMenuItem);
}

export async function deleteMenuItem(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/menu/api/items/${id}/`, {
    method: "DELETE",
    headers: { ...authHeaders() },
    credentials: "include",
  });
  if (res.status === 401) throw new Error("LOGIN_REQUIRED");
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to delete menu item"));
}