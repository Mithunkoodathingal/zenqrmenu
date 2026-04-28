import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchRestaurantProfile,
  updateRestaurantProfile,
  fetchPublicMenu,
  fetchTables,
  createTable,
  deleteTable,
  type RestaurantProfile,
} from "@/lib/restaurantApi";

export function useRestaurantProfile() {
  return useQuery({
    queryKey: ["restaurantProfile"],
    queryFn: fetchRestaurantProfile,
    retry: (count, error) => error.message !== "LOGIN_REQUIRED" && count < 2,
  });
}

export function useUpdateRestaurantProfile() {
  const queryClient = useQueryClient();
  return useMutation<RestaurantProfile, Error, Record<string, unknown>>({
    mutationFn: (data: Record<string, unknown>) => updateRestaurantProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["restaurantProfile"] });
      queryClient.invalidateQueries({ queryKey: ["publicMenu"] });
    },
  });
}

export function useTables() {
  return useQuery({
    queryKey: ["tables"],
    queryFn: fetchTables,
    retry: (count, error) => error.message !== "LOGIN_REQUIRED" && count < 2,
  });
}

export function useCreateTable() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tableNumber: number) => createTable(tableNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tables"] });
    },
  });
}

export function useDeleteTable() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tableId: number) => deleteTable(tableId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tables"] });
    },
  });
}

export function usePublicMenu(tableId: string | null) {
  return useQuery({
    queryKey: ["publicMenu", tableId],
    queryFn: () => fetchPublicMenu(tableId!),
    enabled: !!tableId,
    staleTime: 0,
  });
}
