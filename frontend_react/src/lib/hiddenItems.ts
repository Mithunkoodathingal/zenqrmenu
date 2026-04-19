export type HiddenItemOverrides = Record<number, boolean>;

export const HIDDEN_ITEMS_STORAGE_KEY = "zenqr-hidden-item-overrides";
export const HIDDEN_ITEMS_CHANGED_EVENT = "zenqr-hidden-items-changed";

export const readHiddenItemOverrides = (): HiddenItemOverrides => {
  if (typeof window === "undefined") return {};

  try {
    const raw = window.localStorage.getItem(HIDDEN_ITEMS_STORAGE_KEY);
    if (!raw) return {};

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};

    const overrides: HiddenItemOverrides = {};
    Object.entries(parsed as Record<string, unknown>).forEach(([key, value]) => {
      if (typeof value === "boolean") {
        overrides[Number(key)] = value;
      }
    });

    return overrides;
  } catch {
    return {};
  }
};

export const writeHiddenItemOverrides = (overrides: HiddenItemOverrides) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(HIDDEN_ITEMS_STORAGE_KEY, JSON.stringify(overrides));
  window.dispatchEvent(new CustomEvent(HIDDEN_ITEMS_CHANGED_EVENT));
};