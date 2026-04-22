const NON_VEG_MARKER = "\u2063\u2060\u200B\u2060\u2063";

const VEG_TYPE_TOKENS = new Set(["veg", "vegetarian", "pure_veg", "pureveg", "v", "true", "1"]);
const NON_VEG_TYPE_TOKENS = new Set([
  "non_veg",
  "nonveg",
  "non_vegetarian",
  "nonvegetarian",
  "nveg",
  "nv",
  "false",
  "0",
]);

export function stripMenuItemTypeMarker(description?: string | null): string {
  if (!description) return "";
  return description.split(NON_VEG_MARKER).join("").trimEnd();
}

export function encodeMenuItemDescription(description: string, isVeg?: boolean): string {
  const cleanDescription = stripMenuItemTypeMarker(description);
  return isVeg === false ? `${cleanDescription}${NON_VEG_MARKER}` : cleanDescription;
}

function parseMenuItemTypeValue(value: unknown): boolean | undefined {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (value === 1) return true;
    if (value === 0) return false;
  }
  if (typeof value !== "string") return undefined;

  const normalizedValue = value.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (!normalizedValue) return undefined;
  if (VEG_TYPE_TOKENS.has(normalizedValue)) return true;
  if (NON_VEG_TYPE_TOKENS.has(normalizedValue)) return false;

  return undefined;
}

export function extractMenuItemType(description?: string | null) {
  const rawDescription = description ?? "";
  return {
    description: stripMenuItemTypeMarker(rawDescription),
    isVeg: !rawDescription.includes(NON_VEG_MARKER),
  };
}

export function resolveMenuItemIsVeg(description: string | null | undefined, ...typeValues: unknown[]) {
  for (const value of typeValues) {
    const parsedValue = parseMenuItemTypeValue(value);
    if (typeof parsedValue === "boolean") return parsedValue;
  }

  return extractMenuItemType(description).isVeg;
}