import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, Clock, ChefHat, Eye, Loader2, RefreshCw, XCircle, CheckCircle } from "lucide-react";
import { fetchOrders, updateOrderStatus, type Order } from "@/lib/orderApi";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

const statusConfig = {
  pending: { label: "New Order", color: "bg-orange-100 text-orange-700 border-orange-200", icon: Clock },
  confirmed: { label: "Confirmed", color: "bg-blue-100 text-blue-700 border-blue-200", icon: CheckCircle },
  preparing: { label: "Preparing", color: "bg-blue-100 text-blue-700 border-blue-200", icon: ChefHat },
  completed: { label: "Completed", color: "bg-green-100 text-green-700 border-green-200", icon: Check },
  cancelled: { label: "Cancelled", color: "bg-red-100 text-red-700 border-red-200", icon: XCircle },
};

interface OrdersManagerProps {
  onPendingCountChange?: (count: number) => void;
}

const OrdersManager = ({ onPendingCountChange }: OrdersManagerProps = {}) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | Order["status"]>("all");
  const [expandedOrder, setExpandedOrder] = useState<number | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const loadOrders = useCallback(async () => {
    try {
      const data = await fetchOrders();
      setOrders(data);
    } catch (err) {
      console.error("Failed to load orders:", err);
      toast.error("Failed to load orders");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOrders();
    // Poll every 30s for new orders
    const interval = setInterval(loadOrders, 30000);
    return () => clearInterval(interval);
  }, [loadOrders]);

  // Notify parent of pending count changes
  useEffect(() => {
    const pendingCount = orders.filter((o) => o.status === "pending").length;
    onPendingCountChange?.(pendingCount);
  }, [orders, onPendingCountChange]);

  const handleStatusUpdate = async (orderId: number, newStatus: Order["status"]) => {
    setUpdatingId(orderId);
    try {
      const updated = await updateOrderStatus(orderId, newStatus);
      setOrders((prev) =>
        prev.map((o) => (o.id === orderId ? { ...o, ...updated } : o))
      );
      toast.success(`Order #${orderId} marked as ${newStatus}`);
    } catch {
      toast.error("Failed to update order status");
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredOrders = filter === "all" ? orders : orders.filter((o) => o.status === filter);

  const counts = {
    all: orders.length,
    pending: orders.filter((o) => o.status === "pending").length,
    confirmed: orders.filter((o) => o.status === "confirmed").length,
    preparing: orders.filter((o) => o.status === "preparing").length,
    completed: orders.filter((o) => o.status === "completed").length,
    cancelled: orders.filter((o) => o.status === "cancelled").length,
  };

  const filterTabs: Array<"all" | Order["status"]> = ["all", "pending", "confirmed", "preparing", "completed"];

  const formatTime = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const relative = formatDistanceToNow(date, { addSuffix: true });
      const absolute = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      return `${absolute} (${relative})`;
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold font-heading">View Orders</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {counts.pending} pending
          </span>
          {counts.pending > 0 && (
            <span className="h-2.5 w-2.5 rounded-full bg-primary animate-pulse" />
          )}
          <Button variant="ghost" size="icon" onClick={() => { setLoading(true); loadOrders(); }} title="Refresh orders">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {filterTabs.map((f) => (
          <Button
            key={f}
            variant={filter === f ? "hero" : "outline"}
            size="sm"
            onClick={() => setFilter(f)}
            className="capitalize"
          >
            {f === "all" ? "All Orders" : statusConfig[f].label}
            <span className="ml-1.5 text-xs opacity-70">({counts[f]})</span>
          </Button>
        ))}
      </div>

      {/* Orders List */}
      <div className="space-y-4">
        {filteredOrders.length === 0 ? (
          <Card className="p-8 text-center shadow-card">
            <p className="text-muted-foreground">
              {orders.length === 0 ? "No orders yet. Orders will appear here when customers place them from the menu." : "No orders to show"}
            </p>
          </Card>
        ) : (
          filteredOrders.map((order) => {
            const config = statusConfig[order.status] || statusConfig.pending;
            const StatusIcon = config.icon;
            const isExpanded = expandedOrder === order.id;
            const isUpdating = updatingId === order.id;

            return (
              <Card key={order.id} className="shadow-card overflow-hidden">
                {/* Order Header */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => setExpandedOrder(isExpanded ? null : order.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col items-center">
                      <span className="text-xs text-muted-foreground">Table</span>
                      <span className="text-lg font-bold text-primary">{order.table_number}</span>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">#{order.id}</span>
                        <Badge variant="outline" className={`text-xs ${config.color}`}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {config.label}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {order.customer_name && `${order.customer_name} · `}
                        ₹{order.total_price} · {formatTime(order.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="border-t px-4 pb-4">
                    {order.items && order.items.length > 0 ? (
                      <div className="py-3 space-y-2">
                        {order.items.map((item, i) => (
                          <div key={i} className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-muted-foreground">{item.quantity}×</span>
                              <span>{item.name}</span>
                            </div>
                            {item.price > 0 && (
                              <span className="text-muted-foreground">₹{item.price * item.quantity}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="py-3 text-sm text-muted-foreground italic">No item details available</p>
                    )}
                    {order.customer_phone && (
                      <p className="text-xs text-muted-foreground mb-2">📞 {order.customer_phone}</p>
                    )}
                    <div className="flex items-center justify-between pt-3 border-t">
                      <span className="font-semibold">Total: ₹{order.total_price}</span>
                      <div className="flex gap-2">
                        {order.status === "pending" && (
                          <Button
                            size="sm"
                            variant="hero"
                            disabled={isUpdating}
                            onClick={(e) => { e.stopPropagation(); handleStatusUpdate(order.id, "preparing"); }}
                          >
                            {isUpdating ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <ChefHat className="h-3.5 w-3.5 mr-1" />}
                            Start Preparing
                          </Button>
                        )}
                        {(order.status === "confirmed" || order.status === "preparing") && (
                          <Button
                            size="sm"
                            variant="hero"
                            disabled={isUpdating}
                            onClick={(e) => { e.stopPropagation(); handleStatusUpdate(order.id, "completed"); }}
                          >
                            {isUpdating ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Check className="h-3.5 w-3.5 mr-1" />}
                            Mark Complete
                          </Button>
                        )}
                        {order.status === "completed" && (
                          <span className="text-sm text-green-600 font-medium flex items-center gap-1">
                            <Check className="h-4 w-4" /> Done
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
};

export default OrdersManager;
