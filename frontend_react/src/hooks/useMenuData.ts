import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import {
  fetchCategories,
  fetchMenuItems,
  createCategory,
  updateCategory,
  deleteCategory,
  createMenuItem,
  updateMenuItem,
  deleteMenuItem,
  type ApiCategory,
  type ApiMenuItem,
  type MenuItemInput,
} from "@/lib/menuApi";

export function useCategories() {
  return useQuery<ApiCategory[]>({
    queryKey: ["categories"],
    queryFn: fetchCategories,
    retry: (count, error) => error.message !== "LOGIN_REQUIRED" && count < 2,
  });
}

export function useMenuItems() {
  return useQuery<ApiMenuItem[]>({
    queryKey: ["menuItems"],
    queryFn: fetchMenuItems,
    retry: (count, error) => error.message !== "LOGIN_REQUIRED" && count < 2,
  });
}

export function useMenuMutations() {
  const qc = useQueryClient();
  const { toast } = useToast();

  const onSuccess = (msg: string, keys: string[]) => {
    keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    qc.invalidateQueries({ queryKey: ["publicMenu"] });
    toast({ title: msg });
  };
  const onError = (msg: string) => {
    toast({
      title: "Error",
      description: msg === "LOGIN_REQUIRED" ? "Please log in again and retry." : msg,
      variant: "destructive",
    });
  };

  const addCategory = useMutation({
    mutationFn: (name: string) => createCategory(name),
    onSuccess: () => onSuccess("Category added", ["categories"]),
    onError: (e) => onError(e.message),
  });

  const editCategory = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ApiCategory> }) => updateCategory(id, data),
    onSuccess: () => onSuccess("Category updated", ["categories"]),
    onError: (e) => onError(e.message),
  });

  const removeCategory = useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: () => onSuccess("Category deleted", ["categories", "menuItems"]),
    onError: (e) => onError(e.message),
  });

  const addItem = useMutation({
    mutationFn: (data: MenuItemInput) => createMenuItem(data),
    onSuccess: () => onSuccess("Item added", ["menuItems"]),
    onError: (e) => onError(e.message),
  });

  const editItem = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<MenuItemInput> }) => updateMenuItem(id, data),
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey: ["menuItems"] });

      const previousItems = qc.getQueryData<ApiMenuItem[]>(["menuItems"]);

      if (previousItems) {
        qc.setQueryData<ApiMenuItem[]>(
          ["menuItems"],
          previousItems.map((item) => {
            if (item.id !== id) return item;

            const nextItem: ApiMenuItem = { ...item };

            if (typeof data.name === "string") nextItem.name = data.name;
            if (typeof data.price === "number") nextItem.price = data.price;
            if (typeof data.description === "string") nextItem.description = data.description;
            if (typeof data.category === "number") nextItem.category = data.category;
            if (typeof data.image === "string" || data.image === null) nextItem.image = data.image as string | null;

            if (typeof data.is_paused === "boolean") {
              nextItem.is_available = !data.is_paused;
            } else if (typeof data.is_available === "boolean") {
              nextItem.is_available = data.is_available;
            }

            return nextItem;
          }),
        );
      }

      return { previousItems };
    },
    onSuccess: (updatedItem, { data }) => {
      // Backend doesn't return is_paused in response, so is_available may be stale.
      // Override with the value we sent if we toggled pause.
      const corrected = { ...updatedItem };
      if (typeof data.is_paused === "boolean") {
        corrected.is_available = !data.is_paused;
      } else if (typeof data.is_available === "boolean") {
        corrected.is_available = data.is_available;
      }
      qc.setQueryData<ApiMenuItem[]>(["menuItems"], (current = []) =>
        current.map((item) => (item.id === corrected.id ? corrected : item)),
      );
      onSuccess("Item updated", ["menuItems"]);
    },
    onError: (e, _variables, context) => {
      if (context?.previousItems) {
        qc.setQueryData(["menuItems"], context.previousItems);
      }
      onError(e.message);
    },
  });

  const removeItem = useMutation({
    mutationFn: (id: number) => deleteMenuItem(id),
    onSuccess: () => onSuccess("Item deleted", ["menuItems"]),
    onError: (e) => onError(e.message),
  });

  return { addCategory, editCategory, removeCategory, addItem, editItem, removeItem };
}
