import { useState, useRef, useCallback, useEffect } from "react";
import { useSearchParams, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShoppingCart, Plus, Minus, X, Send, Loader2, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, ChefHat, CheckCircle2, Clock, Utensils, PartyPopper } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { usePublicMenu } from "@/hooks/useRestaurantData";
import { resolveImageUrl } from "@/lib/restaurantApi";
import { createOrder, fetchPublicOrder, type Order } from "@/lib/orderApi";
import { toast } from "sonner";

const ACTIVE_ORDER_KEY = (tableId: string) => `zenqr_active_order_${tableId}`;

const STATUS_STEPS = [
  { key: "pending", label: "Order Received", icon: Clock, description: "Waiting for the kitchen to confirm" },
  { key: "confirmed", label: "Confirmed", icon: CheckCircle2, description: "Kitchen has confirmed your order" },
  { key: "preparing", label: "Preparing", icon: ChefHat, description: "Your food is being prepared" },
  { key: "ready", label: "Ready for Delivery", icon: Utensils, description: "Your food is on its way to your table" },
  { key: "completed", label: "Completed", icon: PartyPopper, description: "Enjoy! Table is ready for the next order" },
] as const;

function getStatusStepIndex(status: string): number {
  switch (status) {
    case "pending":
      return 0;
    case "confirmed":
      return 1;
    case "preparing":
      return 2;
    case "ready":
      return 3;
    case "completed":
      return 4;
    case "cancelled":
      return -1;
    default:
      return 0;
  }
}

function normalizeClientOrder(order: Order): Order {
  return {
    ...order,
    id: Number(order.id),
    table: Number(order.table ?? 0),
    table_number: String(order.table_number ?? order.table ?? ""),
    total_price: Number(order.total_price ?? 0),
    status: (order.status || "pending") as Order["status"],
    items: Array.isArray(order.items) ? order.items : [],
  };
}

function mergeOrderUpdate(currentOrder: Order, incomingOrder: Order): Order {
  const normalizedCurrent = normalizeClientOrder(currentOrder);
  const normalizedIncoming = normalizeClientOrder(incomingOrder);

  return {
    ...normalizedCurrent,
    ...normalizedIncoming,
    id: normalizedIncoming.id || normalizedCurrent.id,
    items: normalizedIncoming.items.length > 0 ? normalizedIncoming.items : normalizedCurrent.items,
    customer_name: normalizedIncoming.customer_name ?? normalizedCurrent.customer_name,
    customer_phone: normalizedIncoming.customer_phone ?? normalizedCurrent.customer_phone,
    table_number: normalizedIncoming.table_number || normalizedCurrent.table_number,
    total_price: normalizedIncoming.total_price > 0 ? normalizedIncoming.total_price : normalizedCurrent.total_price,
  };
}

type CartItem = {
  id: number;
  name: string;
  price: number;
  quantity: number;
};

const MenuViewPage = () => {
  const { tableId: routeTableId } = useParams();
  const [searchParams] = useSearchParams();
  const tableId = routeTableId || searchParams.get("table") || "";

  const [activeCategory, setActiveCategory] = useState<number | "all">("all");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [showCart, setShowCart] = useState(false);
  const [orderPlaced, setOrderPlaced] = useState(false);
  const [isPlacing, setIsPlacing] = useState(false);
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  const [activeOrders, setActiveOrders] = useState<Order[]>([]);
  const catScrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = useCallback(() => {
    const el = catScrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 2);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 2);
  }, []);

  useEffect(() => {
    const timers = [
      setTimeout(checkScroll, 100),
      setTimeout(checkScroll, 500),
      setTimeout(checkScroll, 1500),
    ];
    window.addEventListener("resize", checkScroll);
    return () => {
      timers.forEach(clearTimeout);
      window.removeEventListener("resize", checkScroll);
    };
  }, [checkScroll]);

  const scrollCats = (dir: "left" | "right") => {
    catScrollRef.current?.scrollBy({ left: dir === "left" ? -150 : 150, behavior: "smooth" });
    setTimeout(checkScroll, 350);
  };

  const toggleDesc = (id: number) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const { data: menuData, isLoading, isError, error } = usePublicMenu(tableId || null);

  const addToCart = (item: { id: number; name: string; price: number }) => {
    setCart((prev) => {
      const existing = prev.find((c) => c.id === item.id);
      if (existing) return prev.map((c) => c.id === item.id ? { ...c, quantity: c.quantity + 1 } : c);
      return [...prev, { id: item.id, name: item.name, price: item.price, quantity: 1 }];
    });
  };

  const updateQuantity = (id: number, delta: number) => {
    setCart((prev) =>
      prev.map((c) => c.id === id ? { ...c, quantity: Math.max(0, c.quantity + delta) } : c).filter((c) => c.quantity > 0)
    );
  };

  const getItemQty = (id: number) => cart.find((c) => c.id === id)?.quantity || 0;
  const totalItems = cart.reduce((s, c) => s + c.quantity, 0);
  const totalPrice = cart.reduce((s, c) => s + c.price * c.quantity, 0);

  // ─── Restore active orders from localStorage on mount ───
  useEffect(() => {
    if (!tableId) return;
    try {
      const raw = localStorage.getItem(ACTIVE_ORDER_KEY(tableId));
      if (!raw) return;
      const saved = JSON.parse(raw);
      const restoredOrders = Array.isArray(saved) ? saved : [saved];
      const normalizedOrders = restoredOrders
        .filter((order: Order | null | undefined) => order && Number.isFinite(Number(order.id)))
        .map((order: Order) => normalizeClientOrder(order));

      if (normalizedOrders.length > 0) {
        setActiveOrders(normalizedOrders);
      }
    } catch {
      /* ignore */
    }
  }, [tableId]);

  // ─── Persist whenever activeOrders changes ───
  useEffect(() => {
    if (!tableId) return;
    try {
      if (activeOrders.length === 0) {
        localStorage.removeItem(ACTIVE_ORDER_KEY(tableId));
      } else {
        localStorage.setItem(ACTIVE_ORDER_KEY(tableId), JSON.stringify(activeOrders));
      }
    } catch { /* ignore */ }
  }, [activeOrders, tableId]);

  // ─── Poll status for any in-flight orders (every 4s) ───
  // Depend on a stable comma-joined list of in-flight IDs so the interval
  // is not torn down & recreated on every state update.
  const inFlightIdsKey = activeOrders
    .filter((o) => o.status !== "completed" && o.status !== "cancelled")
    .map((o) => o.id)
    .sort((a, b) => a - b)
    .join(",");

  useEffect(() => {
    if (!tableId || !inFlightIdsKey) return;
    const ids = inFlightIdsKey.split(",").map((id) => Number(id)).filter(Number.isFinite);
    if (ids.length === 0) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const updates = await Promise.all(ids.map((id) => fetchPublicOrder(id)));
        if (cancelled) return;
        console.log("[MenuView] poll updates:", updates.map((u) => u && { id: u.id, status: u.status }));
        const updatesById = new Map(
          updates
            .filter((update): update is Order => Boolean(update?.id))
            .map((update) => [Number(update.id), normalizeClientOrder(update)])
        );

        setActiveOrders((prev) => {
          let hasChanged = false;

          const nextOrders = prev.map((order) => {
            const currentOrder = normalizeClientOrder(order);
            const match = updatesById.get(Number(currentOrder.id));
            if (!match) return currentOrder;

            const nextOrder = mergeOrderUpdate(currentOrder, match);
            const orderChanged =
              nextOrder.status !== currentOrder.status ||
              nextOrder.total_price !== currentOrder.total_price ||
              nextOrder.table !== currentOrder.table ||
              nextOrder.table_number !== currentOrder.table_number ||
              nextOrder.customer_name !== currentOrder.customer_name ||
              nextOrder.customer_phone !== currentOrder.customer_phone ||
              nextOrder.items.length !== currentOrder.items.length;

            if (orderChanged) {
              hasChanged = true;
              console.log(`[MenuView] order #${currentOrder.id} status: ${currentOrder.status} -> ${nextOrder.status}`);
              return nextOrder;
            }

            return currentOrder;
          });

          return hasChanged ? [...nextOrders] : prev;
        });
      } catch (err) {
        console.warn("[MenuView] poll failed:", err);
      }
    };

    // Fire immediately, then every 4s.
    poll();
    const interval = setInterval(poll, 4000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [tableId, inFlightIdsKey]);

  const dismissOrder = (orderId: number) => {
    setActiveOrders((prev) => prev.filter((o) => o.id !== orderId));
  };

  const placeOrder = async () => {
    if (cart.length === 0) return;

    setIsPlacing(true);
    try {
      const newOrder = await createOrder({
        restaurant: menuData.restaurant.id,
        table: Number(tableId),
        customer_name: customerName.trim() || undefined,
        customer_phone: customerPhone.trim() || undefined,
        items: cart.map((c) => ({
          food_item_id: c.id,
          quantity: c.quantity,
          selected_addons_ids: [],
        })),
      });
      setOrderPlaced(true);
      if (newOrder) {
        setActiveOrders((prev) => [...prev, normalizeClientOrder(newOrder)]);
      }
      setTimeout(() => {
        setCart([]);
        setShowCart(false);
        setOrderPlaced(false);
        setCustomerName("");
        setCustomerPhone("");
      }, 2000);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to place order. Please try again.");
    } finally {
      setIsPlacing(false);
    }
  };

  if (!tableId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="p-8 text-center max-w-sm">
          <h2 className="text-lg font-bold mb-2">Invalid Menu Link</h2>
          <p className="text-sm text-muted-foreground">This QR code or link is missing the restaurant identifier. Please scan a valid QR code.</p>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !menuData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="p-8 text-center max-w-sm">
          <h2 className="text-lg font-bold mb-2">Menu Not Found</h2>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : "Could not load the menu. The restaurant may not exist or the link is invalid."}
          </p>
          <p className="text-xs text-muted-foreground mt-3">Table ID: {tableId}</p>
        </Card>
      </div>
    );
  }

  const { restaurant, categories, items } = menuData;
  const tableLabel = menuData.table_number || tableId;
  const availableItems = items.filter((item) => item.is_available);
  const filteredItems = activeCategory === "all" ? availableItems : availableItems.filter((item) => item.category === activeCategory);

  return (
    <div className="min-h-screen bg-background">
      {/* Cover Photo with overlapping logo */}
      <div className="relative">
        {restaurant.cover_image ? (
          <div className="w-full h-44 sm:h-56 overflow-hidden">
            <img
              src={resolveImageUrl(restaurant.cover_image)}
              alt={`${restaurant.name} cover`}
              className="w-full h-full object-cover"
            />
          </div>
        ) : (
          <div className="w-full h-44 sm:h-56 bg-muted" />
        )}
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-background/70 via-background/25 to-transparent" />
        <div className="absolute bottom-4 left-4 sm:bottom-5 sm:left-5">
          {restaurant.logo ? (
            <img
              src={resolveImageUrl(restaurant.logo)}
              alt={restaurant.name}
              className="h-20 w-20 sm:h-24 sm:w-24 rounded-2xl object-cover border-4 border-background bg-card p-1 shadow-lg"
            />
          ) : (
            <div className="flex h-20 w-20 sm:h-24 sm:w-24 items-center justify-center rounded-2xl bg-primary text-primary-foreground font-bold text-2xl sm:text-3xl border-4 border-background shadow-lg">
              {restaurant.name.charAt(0)}
            </div>
          )}
        </div>
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 bg-card border-b shadow-sm">
        <div className="max-w-lg mx-auto px-4 pt-14 pb-3 sm:pt-16">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold font-heading">{restaurant.name}</h1>
              <p className="text-xs text-muted-foreground -mt-0.5 line-clamp-1">
                {restaurant.address?.split(",")[0]?.trim() || `Table ${tableLabel}`}
              </p>
            </div>
            <Badge variant="outline" className="text-xs font-medium">
              Table {tableLabel}
            </Badge>
          </div>
        </div>

        {/* Category Tabs with Arrow Navigation */}
        <div className="max-w-lg mx-auto px-1 pb-2 relative flex items-center">
          {canScrollLeft && (
            <button
              onClick={() => scrollCats("left")}
              className="shrink-0 p-1.5 rounded-full bg-card border border-border shadow-sm text-primary hover:bg-primary hover:text-primary-foreground transition-colors z-10"
              aria-label="Scroll categories left"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          )}
          <div
            ref={catScrollRef}
            onScroll={checkScroll}
            onLoad={checkScroll}
            className="flex gap-2 overflow-x-auto scrollbar-hide px-2 flex-1"
            style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
          >
            <button
              onClick={() => setActiveCategory("all")}
              className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                activeCategory === "all"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              All
            </button>
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                  activeCategory === cat.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {cat.name}
              </button>
            ))}
          </div>
          {canScrollRight && (
            <button
              onClick={() => scrollCats("right")}
              className="shrink-0 p-1.5 rounded-full bg-card border border-border shadow-sm text-primary hover:bg-primary hover:text-primary-foreground transition-colors z-10"
              aria-label="Scroll categories right"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </header>

      {/* Kitchen Status Banners — one per active order */}
      {activeOrders.length > 0 && (
        <div className="max-w-lg mx-auto px-4 pt-4 space-y-3">
          {activeOrders.map((order) => (
            <Card key={order.id} className="p-4 border-primary/30 bg-gradient-to-br from-primary/5 to-transparent shadow-card">
              {order.status === "completed" ? (
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <PartyPopper className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-sm">Order #{order.id} Completed</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Enjoy your meal! You can keep ordering anytime from the menu below.
                    </p>
                    <Button size="sm" variant="outline" className="mt-3 h-8 text-xs" onClick={() => dismissOrder(order.id)}>
                      Dismiss
                    </Button>
                  </div>
                </div>
              ) : order.status === "cancelled" ? (
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-full bg-destructive/10 flex items-center justify-center shrink-0">
                    <X className="h-5 w-5 text-destructive" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-sm">Order #{order.id} Cancelled</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">Please speak to staff if you need help.</p>
                    <Button size="sm" variant="outline" className="mt-3 h-8 text-xs" onClick={() => dismissOrder(order.id)}>
                      Dismiss
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">Kitchen Status</p>
                      <h3 className="font-bold text-sm">Order #{order.id}</h3>
                    </div>
                    <Badge variant="secondary" className="text-[10px] capitalize">
                      {STATUS_STEPS[Math.max(0, getStatusStepIndex(order.status))]?.label || order.status}
                    </Badge>
                  </div>
                  <div className="flex items-start justify-between">
                    {STATUS_STEPS.slice(0, 4).map((step, idx) => {
                      const currentIdx = getStatusStepIndex(order.status);
                      const isDone = idx < currentIdx;
                      const isCurrent = idx === currentIdx;
                      const Icon = step.icon;
                      return (
                        <div key={step.key} className="flex flex-col items-center flex-1 relative">
                          {idx > 0 && (
                            <div
                              className={`absolute right-1/2 top-3 h-0.5 w-full ${
                                isDone || isCurrent ? "bg-primary" : "bg-muted"
                              }`}
                            />
                          )}
                          <div
                            className={`relative h-6 w-6 rounded-full flex items-center justify-center z-10 transition-colors ${
                              isDone
                                ? "bg-primary text-primary-foreground"
                                : isCurrent
                                ? "bg-primary text-primary-foreground ring-4 ring-primary/20 animate-pulse"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            <Icon className="h-3 w-3" />
                          </div>
                          <span
                            className={`text-[9px] mt-1.5 text-center leading-tight px-0.5 ${
                              isCurrent ? "text-foreground font-semibold" : "text-muted-foreground"
                            }`}
                          >
                            {step.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-xs text-muted-foreground mt-3 text-center">
                    {STATUS_STEPS[Math.max(0, getStatusStepIndex(order.status))]?.description}
                  </p>
                </>
              )}
            </Card>
          ))}
          <p className="text-[11px] text-center text-muted-foreground">
            Want more? Just add items below and place another order anytime.
          </p>
        </div>
      )}

      {/* Menu Items */}
      <main className="max-w-lg mx-auto px-4 py-4 pb-24">
        <div className="space-y-3">
          {filteredItems.length === 0 && (
            <p className="text-center text-muted-foreground py-8 text-sm">No items in this category.</p>
          )}
          {filteredItems.map((item) => {
            const qty = getItemQty(item.id);
            const imgUrl = resolveImageUrl(item.image);
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Card className="p-4 shadow-card">
                  <div className="flex justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {(() => {
                          const isVeg = item.is_veg !== false;
                          return (
                            <span className={`h-3.5 w-3.5 rounded-sm border-2 flex items-center justify-center ${isVeg ? 'border-green-600' : 'border-red-600'}`}>
                              <span className={`h-1.5 w-1.5 rounded-full ${isVeg ? 'bg-green-600' : 'bg-red-600'}`} />
                            </span>
                          );
                        })()}
                        <h3 className="font-semibold text-sm">{item.name}</h3>
                      </div>
                      {item.description && (
                        <div className="flex items-start gap-1 mb-2">
                          <p className={`text-xs text-muted-foreground leading-relaxed ${expandedItems.has(item.id) ? "" : "line-clamp-1"}`}>
                            {item.description}
                          </p>
                          {item.description.length > 50 && (
                            <button
                              onClick={() => toggleDesc(item.id)}
                              className="shrink-0 mt-0.5 text-primary hover:text-primary/80 transition-colors"
                              aria-label={expandedItems.has(item.id) ? "Show less" : "Read more"}
                            >
                              {expandedItems.has(item.id) ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                            </button>
                          )}
                        </div>
                      )}
                      <span className="font-bold text-sm">₹{item.price}</span>
                    </div>
                    <div className="flex flex-col items-center gap-2">
                      {imgUrl && (
                        <img src={imgUrl} alt={item.name} className="w-20 h-20 rounded-lg object-cover" />
                      )}
                      {qty === 0 ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-primary text-primary hover:bg-primary hover:text-primary-foreground font-semibold px-5"
                          onClick={() => addToCart(item)}
                        >
                          ADD
                        </Button>
                      ) : (
                        <div className="flex items-center gap-2 bg-primary rounded-lg px-1">
                          <Button size="icon" variant="ghost" className="h-7 w-7 text-primary-foreground hover:bg-primary/80" onClick={() => updateQuantity(item.id, -1)}>
                            <Minus className="h-3.5 w-3.5" />
                          </Button>
                          <span className="text-sm font-bold text-primary-foreground w-4 text-center">{qty}</span>
                          <Button size="icon" variant="ghost" className="h-7 w-7 text-primary-foreground hover:bg-primary/80" onClick={() => updateQuantity(item.id, 1)}>
                            <Plus className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </main>

      {/* Cart Bar */}
      {totalItems > 0 && !showCart && (
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          className="fixed bottom-0 left-0 right-0 z-50 p-4"
        >
          <div className="max-w-lg mx-auto">
            <Button variant="hero" className="w-full py-6 text-base shadow-xl" onClick={() => setShowCart(true)}>
              <ShoppingCart className="h-5 w-5 mr-2" />
              {totalItems} item{totalItems > 1 ? "s" : ""} · ₹{totalPrice}
              <span className="ml-auto text-sm opacity-80">View Cart →</span>
            </Button>
          </div>
        </motion.div>
      )}

      {/* Cart Drawer */}
      <AnimatePresence>
        {showCart && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.5 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black z-50" onClick={() => setShowCart(false)} />
            <motion.div
              initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed bottom-0 left-0 right-0 z-50 bg-card rounded-t-2xl max-h-[80vh] overflow-auto"
            >
              <div className="max-w-lg mx-auto p-5">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold font-heading">Your Order</h2>
                  <Button size="icon" variant="ghost" onClick={() => setShowCart(false)}><X className="h-5 w-5" /></Button>
                </div>
                {orderPlaced ? (
                  <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-center py-8">
                    <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                      <Send className="h-8 w-8 text-green-600" />
                    </div>
                    <h3 className="text-xl font-bold mb-1">Order Placed!</h3>
                    <p className="text-muted-foreground text-sm">Your order has been sent to the kitchen</p>
                  </motion.div>
                ) : (
                  <>
                    <div className="space-y-3 mb-4">
                      {cart.map((item) => (
                        <div key={item.id} className="flex items-center justify-between py-2 border-b last:border-0">
                          <div>
                            <p className="font-medium text-sm">{item.name}</p>
                            <p className="text-xs text-muted-foreground">₹{item.price} each</p>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1.5 bg-muted rounded-lg px-1">
                              <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => updateQuantity(item.id, -1)}><Minus className="h-3 w-3" /></Button>
                              <span className="text-sm font-semibold w-4 text-center">{item.quantity}</span>
                              <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => updateQuantity(item.id, 1)}><Plus className="h-3 w-3" /></Button>
                            </div>
                            <span className="font-semibold text-sm w-14 text-right">₹{item.price * item.quantity}</span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Customer Details (optional) */}
                    <div className="space-y-3 mb-4 p-3 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground font-medium">Optional Details</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label htmlFor="customer-name" className="text-xs">Name</Label>
                          <Input
                            id="customer-name"
                            placeholder="Your name"
                            value={customerName}
                            onChange={(e) => setCustomerName(e.target.value)}
                            className="h-8 text-sm"
                          />
                        </div>
                        <div>
                          <Label htmlFor="customer-phone" className="text-xs">Phone</Label>
                          <Input
                            id="customer-phone"
                            placeholder="Phone number"
                            value={customerPhone}
                            onChange={(e) => setCustomerPhone(e.target.value)}
                            className="h-8 text-sm"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between py-3 border-t font-bold">
                      <span>Total</span>
                      <span>₹{totalPrice}</span>
                    </div>
                    <Button
                      variant="hero"
                      className="w-full py-6 text-base mt-2"
                      onClick={placeOrder}
                      disabled={isPlacing}
                    >
                      {isPlacing ? (
                        <><Loader2 className="h-5 w-5 mr-2 animate-spin" /> Placing Order...</>
                      ) : (
                        <><Send className="h-5 w-5 mr-2" /> Place Order</>
                      )}
                    </Button>
                  </>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MenuViewPage;
