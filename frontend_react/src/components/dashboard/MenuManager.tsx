import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import {
  Plus,
  Trash2,
  Edit,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  Eye,
  EyeOff,
  Loader2,
  Check,
  X,
} from "lucide-react";
import { useCategories, useMenuItems, useMenuMutations } from "@/hooks/useMenuData";
import { resolveMenuImageUrl, type ApiMenuItem, type MenuItemInput } from "@/lib/menuApi";
import { useToast } from "@/hooks/use-toast";
import { isUnlimitedLimit, useCanAddMenuItem, useSubscription } from "@/hooks/useSubscription";
import { useRestaurantProfile } from "@/hooks/useRestaurantData";
import { Settings } from "lucide-react";

type MenuItemFormState = {
  name: string;
  price: string;
  description: string;
  category: number | "";
  imageFile: File | null;
  imageUrl: string;
};

const createEmptyItemForm = (defaultCategory?: number): MenuItemFormState => ({
  name: "",
  price: "",
  description: "",
  category: defaultCategory ?? "",
  imageFile: null,
  imageUrl: "",
});

const MenuManager = ({ onNavigateToRestaurant }: { onNavigateToRestaurant?: () => void }) => {
  const { data: restaurant, isLoading: restaurantLoading } = useRestaurantProfile();
  const { data: categories = [], isLoading: catsLoading } = useCategories();
  const { data: items = [], isLoading: itemsLoading } = useMenuItems();
  const { addCategory, removeCategory, addItem, editItem, removeItem } = useMenuMutations();
  const { toast } = useToast();
  const { data: subscription } = useSubscription();
  const { allowed: canAddItem, limit: itemLimit, reason: itemGateReason } = useCanAddMenuItem(items.length);
  const showItemUsage = !!subscription?.is_active && !isUnlimitedLimit(itemLimit);

  const [expandedCats, setExpandedCats] = useState<Set<number>>(new Set());
  const [hasInitializedExpanded, setHasInitializedExpanded] = useState(false);
  const [showAddItem, setShowAddItem] = useState(false);
  const [showAddCategory, setShowAddCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newItem, setNewItem] = useState<MenuItemFormState>(createEmptyItemForm());
  const [editingItem, setEditingItem] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<MenuItemFormState>(createEmptyItemForm());
  

  useEffect(() => {
    if (!hasInitializedExpanded && categories.length > 0) {
      setExpandedCats(new Set(categories.map((category) => category.id)));
      setHasInitializedExpanded(true);
    }
  }, [categories, hasInitializedExpanded]);

  useEffect(() => {
    if (categories.length > 0) {
      setNewItem((prev) => (prev.category === "" ? { ...prev, category: categories[0].id } : prev));
    }
  }, [categories]);

  const toggleCategory = (id: number) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const resetNewItem = () => {
    setNewItem(createEmptyItemForm(categories[0]?.id));
  };

  const isItemHidden = (item: ApiMenuItem) => !item.is_available;

  const handleAddCategory = () => {
    const trimmedName = newCategoryName.trim();
    if (!trimmedName) {
      toast({ title: "Category name required", variant: "destructive" });
      return;
    }

    addCategory.mutate(trimmedName, {
      onSuccess: () => {
        setNewCategoryName("");
        setShowAddCategory(false);
      },
    });
  };

  const handleOpenAddItem = () => {
    if (!canAddItem) {
      toast({ title: "Limit reached", description: itemGateReason, variant: "destructive" });
      return;
    }
    if (!categories.length) {
      toast({ title: "Add a category first", description: "Create at least one category before adding an item.", variant: "destructive" });
      return;
    }

    resetNewItem();
    setShowAddCategory(false);
    setShowAddItem(true);
  };

  const handleAddItem = () => {
    if (!newItem.name.trim() || !newItem.price || newItem.category === "") {
      toast({ title: "Missing required fields", description: "Name, price, and category are required.", variant: "destructive" });
      return;
    }

    const payload: MenuItemInput = {
      name: newItem.name.trim(),
      price: Number(newItem.price),
      description: newItem.description.trim(),
      category: Number(newItem.category),
      is_paused: false,
      ...(newItem.imageFile ? { image: newItem.imageFile } : {}),
    };

    addItem.mutate(payload, {
      onSuccess: () => {
        resetNewItem();
        setShowAddItem(false);
        setExpandedCats((prev) => new Set(prev).add(Number(payload.category)));
      },
    });
  };

  const handleTogglePause = (item: ApiMenuItem) => {
    const nextHidden = item.is_available;

    editItem.mutate({
      id: item.id,
      data: {
        is_paused: nextHidden,
        is_available: !nextHidden,
      },
    });
  };

  const startEdit = (item: ApiMenuItem) => {
    setExpandedCats((prev) => new Set(prev).add(item.category));
    setEditingItem(item.id);
    setEditForm({
      name: item.name,
      price: String(item.price),
      description: item.description,
      category: item.category,
      imageFile: null,
      imageUrl: item.image ?? "",
    });
  };

  const saveEdit = (id: number) => {
    if (!editForm.name.trim() || !editForm.price || editForm.category === "") {
      toast({ title: "Missing required fields", description: "Name, price, and category are required.", variant: "destructive" });
      return;
    }

    const payload: Partial<MenuItemInput> = {
      name: editForm.name.trim(),
      price: Number(editForm.price),
      description: editForm.description.trim(),
      category: Number(editForm.category),
      ...(editForm.imageFile ? { image: editForm.imageFile } : {}),
    };

    editItem.mutate(
      { id, data: payload },
      {
        onSuccess: () => {
          setEditingItem(null);
          setEditForm(createEmptyItemForm());
        },
      },
    );
  };

  if (restaurantLoading || catsLoading || itemsLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading menu...</span>
      </div>
    );
  }

  if (!restaurant || (typeof restaurant === "object" && !("id" in restaurant))) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
          <Settings className="h-8 w-8 text-primary" />
        </div>
        <h2 className="text-xl font-bold font-heading mb-2">No Restaurant Found</h2>
        <p className="text-muted-foreground mb-6 max-w-md">
          You need to create your restaurant profile first before managing your menu. Head over to the Restaurant tab to get started.
        </p>
        {onNavigateToRestaurant && (
          <Button variant="hero" onClick={onNavigateToRestaurant}>
            <Settings className="mr-2 h-4 w-4" /> Go to Restaurant Settings
          </Button>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl sm:text-2xl font-bold font-heading">Manage Menu</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => { setShowAddItem(false); setShowAddCategory((prev) => !prev); }}>
            <Plus className="mr-1 h-4 w-4" /> Category
          </Button>
          <Button variant="hero" size="sm" onClick={handleOpenAddItem}>
            <Plus className="mr-1 h-4 w-4" /> Item {showItemUsage ? `(${items.length}/${itemLimit})` : ""}
          </Button>
        </div>
      </div>

      {showAddCategory && (
        <Card className="mb-4 p-4 shadow-card">
          <h3 className="mb-3 font-semibold">Add Category</h3>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} placeholder="Category name" />
            <Button variant="hero" onClick={handleAddCategory} disabled={addCategory.isPending}>
              {addCategory.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
            </Button>
            <Button variant="outline" onClick={() => setShowAddCategory(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {showAddItem && (
        <Card className="mb-4 p-4 shadow-card">
          <h3 className="mb-3 font-semibold">Add Menu Item</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label>Item Name</Label>
              <Input value={newItem.name} onChange={(e) => setNewItem({ ...newItem, name: e.target.value })} placeholder="e.g. Butter Chicken" className="mt-1" />
            </div>
            <div>
              <Label>Price (₹)</Label>
              <Input type="number" min="0" value={newItem.price} onChange={(e) => setNewItem({ ...newItem, price: e.target.value })} placeholder="e.g. 349" className="mt-1" />
            </div>
            <div className="sm:col-span-2">
              <Label>Description</Label>
              <Textarea value={newItem.description} onChange={(e) => setNewItem({ ...newItem, description: e.target.value })} placeholder="Brief description..." className="mt-1" rows={2} />
            </div>
            <div>
              <Label>Category</Label>
              <select value={newItem.category} onChange={(e) => setNewItem({ ...newItem, category: Number(e.target.value) })} className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm">
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="new-item-image">Item Image</Label>
              <Input id="new-item-image" type="file" accept="image/*" className="mt-1" onChange={(e) => setNewItem({ ...newItem, imageFile: e.target.files?.[0] ?? null })} />
              <p className="mt-1 text-xs text-muted-foreground">
                {newItem.imageFile ? `Selected: ${newItem.imageFile.name}` : "Optional. Upload a dish photo."}
              </p>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <Button variant="hero" onClick={handleAddItem} disabled={addItem.isPending}>
              {addItem.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
              Add Item
            </Button>
            <Button variant="outline" onClick={() => setShowAddItem(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {categories.length === 0 && (
        <Card className="p-8 text-center shadow-card">
          <p className="text-muted-foreground">No categories yet. Add your first category to get started.</p>
        </Card>
      )}

      <div className="space-y-4">
        {categories.map((cat) => {
          const catItems = items.filter((item) => item.category === cat.id);
          const isExpanded = expandedCats.has(cat.id);

          return (
            <Card key={cat.id} className="overflow-hidden shadow-card">
              <div className="flex w-full cursor-pointer items-center justify-between p-4 transition-colors hover:bg-muted/50" onClick={() => toggleCategory(cat.id)}>
                <div className="flex items-center gap-3">
                  <span className="font-semibold">{cat.name}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{catItems.length} items</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeCategory.mutate(cat.id);
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                </div>
              </div>

              {isExpanded && (
                <div className="border-t">
                  {catItems.length === 0 ? (
                    <p className="p-4 text-center text-sm text-muted-foreground">No items yet</p>
                  ) : (
                    catItems.map((item) => {
                      const isEditing = editingItem === item.id;
                      const imageSrc = resolveMenuImageUrl(item.image);
                      const isHidden = isItemHidden(item);

                      if (isEditing) {
                        return (
                          <div key={item.id} className="border-b bg-muted/20 p-4 last:border-b-0">
                            <div className="grid gap-3 sm:grid-cols-2">
                              <div>
                                <Label>Name</Label>
                                <Input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="mt-1" />
                              </div>
                              <div>
                                <Label>Price (₹)</Label>
                                <Input type="number" min="0" value={editForm.price} onChange={(e) => setEditForm({ ...editForm, price: e.target.value })} className="mt-1" />
                              </div>
                              <div className="sm:col-span-2">
                                <Label>Description</Label>
                                <Textarea value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} className="mt-1" rows={2} />
                              </div>
                              <div>
                                <Label>Category</Label>
                                <select value={editForm.category} onChange={(e) => setEditForm({ ...editForm, category: Number(e.target.value) })} className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm">
                                  {categories.map((category) => (
                                    <option key={category.id} value={category.id}>{category.name}</option>
                                  ))}
                                </select>
                              </div>
                              <div>
                                <Label htmlFor={`edit-item-image-${item.id}`}>Item Image</Label>
                                <Input id={`edit-item-image-${item.id}`} type="file" accept="image/*" className="mt-1" onChange={(e) => setEditForm({ ...editForm, imageFile: e.target.files?.[0] ?? null })} />
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {editForm.imageFile ? `Selected: ${editForm.imageFile.name}` : editForm.imageUrl ? "Current image will be kept unless you replace it." : "Optional. Upload a dish photo."}
                                </p>
                              </div>
                              {editForm.imageUrl && !editForm.imageFile && (
                                <div className="sm:col-span-2">
                                  <img src={resolveMenuImageUrl(editForm.imageUrl)} alt={`${item.name} preview`} className="h-20 w-20 rounded-lg border object-cover" loading="lazy" />
                                </div>
                              )}
                            </div>
                            <div className="mt-3 flex gap-2">
                              <Button size="sm" variant="hero" onClick={() => saveEdit(item.id)} disabled={editItem.isPending}>
                                <Check className="mr-1 h-3.5 w-3.5" /> Save
                              </Button>
                              <Button size="sm" variant="outline" onClick={() => { setEditingItem(null); setEditForm(createEmptyItemForm()); }}>
                                <X className="mr-1 h-3.5 w-3.5" /> Cancel
                              </Button>
                            </div>
                          </div>
                        );
                      }

                      return (
                        <div key={item.id} className={`flex items-center justify-between border-b p-3 sm:p-4 transition-colors hover:bg-muted/30 last:border-b-0 ${isHidden ? "opacity-50" : ""}`}>
                          <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
                            {imageSrc ? (
                              <img src={imageSrc} alt={`${item.name} thumbnail`} className="h-9 w-9 sm:h-10 sm:w-10 shrink-0 rounded-lg border object-cover" loading="lazy" />
                            ) : (
                              <div className="flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-lg bg-accent">
                                <ImageIcon className="h-4 w-4 text-accent-foreground" />
                              </div>
                            )}
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium truncate">{item.name}</p>
                                {isHidden && <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground shrink-0">Hidden</span>}
                              </div>
                              {item.description && (
                                <p className="hidden sm:block text-xs text-muted-foreground truncate">{item.description}</p>
                              )}
                            </div>
                          </div>
                          <div className="flex shrink-0 items-center gap-1 sm:gap-2 ml-2">
                            <span className="text-sm font-semibold whitespace-nowrap">₹{item.price}</span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className={`h-7 w-7 sm:h-8 sm:w-8 ${isHidden ? "text-muted-foreground" : "text-primary"}`}
                              onClick={() => handleTogglePause(item)}
                              disabled={editItem.isPending}
                              title={isHidden ? "Item hidden — click to show" : "Item visible — click to hide"}
                            >
                              {isHidden ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7 sm:h-8 sm:w-8" onClick={() => startEdit(item)}>
                              <Edit className="h-3.5 w-3.5" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7 sm:h-8 sm:w-8 text-destructive" onClick={() => removeItem.mutate(item.id)}>
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default MenuManager;
