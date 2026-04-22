import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { fetchOrders, type Order } from "@/lib/orderApi";
import { useMenuItems, useCategories } from "@/hooks/useMenuData";
import { useTables } from "@/hooks/useRestaurantData";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid,
} from "recharts";
import { TrendingUp, ShoppingCart, Utensils, QrCode, IndianRupee, Clock, CheckCircle, XCircle } from "lucide-react";

const COLORS = ["hsl(24,95%,53%)", "hsl(24,80%,65%)", "hsl(24,60%,75%)", "hsl(200,60%,50%)", "hsl(150,50%,45%)", "hsl(280,50%,55%)"];

type TimeRange = "daily" | "weekly" | "monthly" | "quarterly" | "yearly";

const TIME_RANGES: { key: TimeRange; label: string }[] = [
  { key: "daily", label: "Today" },
  { key: "weekly", label: "7 Days" },
  { key: "monthly", label: "30 Days" },
  { key: "quarterly", label: "90 Days" },
  { key: "yearly", label: "1 Year" },
];

function getDaysForRange(range: TimeRange): number {
  switch (range) {
    case "daily": return 1;
    case "weekly": return 7;
    case "monthly": return 30;
    case "quarterly": return 90;
    case "yearly": return 365;
  }
}

function getDateKey(date: Date, range: TimeRange): string {
  if (range === "daily") return date.toLocaleTimeString("en-IN", { hour: "2-digit" });
  if (range === "weekly") return date.toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });
  if (range === "monthly") return date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  if (range === "quarterly") return date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  return date.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

function getBucketCount(range: TimeRange): number {
  switch (range) {
    case "daily": return 24;
    case "weekly": return 7;
    case "monthly": return 30;
    case "quarterly": return 12;
    case "yearly": return 12;
  }
}

function getBucketDate(now: Date, index: number, total: number, range: TimeRange): Date {
  const d = new Date(now);
  if (range === "daily") {
    d.setHours(d.getHours() - (total - 1 - index), 0, 0, 0);
  } else if (range === "yearly") {
    d.setMonth(d.getMonth() - (total - 1 - index), 1);
  } else if (range === "quarterly") {
    // ~weekly buckets over 90 days
    d.setDate(d.getDate() - (total - 1 - index) * 7);
  } else {
    d.setDate(d.getDate() - (total - 1 - index));
  }
  return d;
}

function isInBucket(orderDate: Date, bucketDate: Date, range: TimeRange): boolean {
  if (range === "daily") {
    return orderDate.getHours() === bucketDate.getHours() &&
      orderDate.toDateString() === bucketDate.toDateString();
  }
  if (range === "yearly") {
    return orderDate.getMonth() === bucketDate.getMonth() &&
      orderDate.getFullYear() === bucketDate.getFullYear();
  }
  if (range === "quarterly") {
    const bStart = new Date(bucketDate);
    const bEnd = new Date(bucketDate);
    bEnd.setDate(bEnd.getDate() + 7);
    return orderDate >= bStart && orderDate < bEnd;
  }
  return orderDate.toDateString() === bucketDate.toDateString();
}

const AnalyticsDashboard = () => {
  const [range, setRange] = useState<TimeRange>("weekly");

  const { data: allOrders = [], isLoading: loadingOrders } = useQuery<Order[]>({
    queryKey: ["orders"],
    queryFn: () => fetchOrders(),
    refetchInterval: 30000,
    retry: (c, e) => (e as Error).message !== "LOGIN_REQUIRED" && c < 2,
  });

  const { data: menuItems = [] } = useMenuItems();
  const { data: categories = [] } = useCategories();
  const { data: tables = [] } = useTables();

  // Filter orders by selected time range
  const orders = useMemo(() => {
    const days = getDaysForRange(range);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    cutoff.setHours(0, 0, 0, 0);
    if (range === "daily") {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return allOrders.filter(o => new Date(o.created_at) >= today);
    }
    return allOrders.filter(o => new Date(o.created_at) >= cutoff);
  }, [allOrders, range]);

  const activeOrders = useMemo(() => orders.filter(o => o.status !== "cancelled"), [orders]);

  const stats = useMemo(() => {
    const totalOrders = activeOrders.length;
    const pending = activeOrders.filter(o => o.status === "pending").length;
    const completed = activeOrders.filter(o => o.status === "completed").length;
    const cancelled = orders.filter(o => o.status === "cancelled").length;
    const totalRevenue = activeOrders.reduce((sum, o) => sum + (o.total_price || 0), 0);
    return { totalOrders, pending, completed, cancelled, totalRevenue };
  }, [orders, activeOrders]);

  // Build chart buckets
  const bucketCount = getBucketCount(range);
  const now = new Date();

  const ordersByBucket = useMemo(() => {
    const buckets: { label: string; orders: number }[] = [];
    for (let i = 0; i < bucketCount; i++) {
      const d = getBucketDate(now, i, bucketCount, range);
      buckets.push({ label: getDateKey(d, range), orders: 0 });
    }
    activeOrders.forEach(o => {
      const od = new Date(o.created_at);
      for (let i = 0; i < bucketCount; i++) {
        const bd = getBucketDate(now, i, bucketCount, range);
        if (isInBucket(od, bd, range)) {
          buckets[i].orders++;
          break;
        }
      }
    });
    return buckets;
  }, [activeOrders, range, bucketCount]);

  const revenueByBucket = useMemo(() => {
    const buckets: { label: string; revenue: number }[] = [];
    for (let i = 0; i < bucketCount; i++) {
      const d = getBucketDate(now, i, bucketCount, range);
      buckets.push({ label: getDateKey(d, range), revenue: 0 });
    }
    activeOrders.forEach(o => {
      const od = new Date(o.created_at);
      for (let i = 0; i < bucketCount; i++) {
        const bd = getBucketDate(now, i, bucketCount, range);
        if (isInBucket(od, bd, range)) {
          buckets[i].revenue += o.total_price || 0;
          break;
        }
      }
    });
    return buckets.map(b => ({ ...b, revenue: Math.round(b.revenue) }));
  }, [activeOrders, range, bucketCount]);

  const topItems = useMemo(() => {
    const counts: Record<string, number> = {};
    activeOrders.forEach(o => {
      o.items?.forEach(item => {
        const name = item.name || "Unknown";
        counts[name] = (counts[name] || 0) + item.quantity;
      });
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, count]) => ({ name, count }));
  }, [activeOrders]);

  const statusData = useMemo(() => {
    const map: Record<string, number> = {};
    orders.forEach(o => {
      map[o.status] = (map[o.status] || 0) + 1;
    });
    return Object.entries(map).map(([status, value]) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1),
      value,
    }));
  }, [orders]);

  const statCards = [
    { label: "Total Orders", value: stats.totalOrders, icon: ShoppingCart, color: "text-primary" },
    { label: "Revenue", value: `₹${stats.totalRevenue.toLocaleString("en-IN")}`, icon: IndianRupee, color: "text-green-600" },
    { label: "Pending", value: stats.pending, icon: Clock, color: "text-yellow-600" },
    { label: "Completed", value: stats.completed, icon: CheckCircle, color: "text-green-600" },
    { label: "Cancelled", value: stats.cancelled, icon: XCircle, color: "text-destructive" },
    { label: "Menu Items", value: menuItems.length, icon: Utensils, color: "text-primary" },
    { label: "Categories", value: categories.length, icon: TrendingUp, color: "text-blue-600" },
    { label: "Tables", value: (tables as any[])?.length || 0, icon: QrCode, color: "text-primary" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-2xl font-bold font-heading">Analytics</h1>
        <div className="flex gap-1.5 flex-wrap">
          {TIME_RANGES.map(tr => (
            <Button
              key={tr.key}
              size="sm"
              variant={range === tr.key ? "hero" : "outline"}
              onClick={() => setRange(tr.key)}
              className="text-xs px-3"
            >
              {tr.label}
            </Button>
          ))}
        </div>
      </div>

      {loadingOrders ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i} className="p-5 animate-pulse">
              <div className="h-4 bg-muted rounded w-24 mb-2" />
              <div className="h-8 bg-muted rounded w-16" />
            </Card>
          ))}
        </div>
      ) : (
        <>
          {/* Stat Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            {statCards.map(s => (
              <Card key={s.label} className="p-4 shadow-card">
                <div className="flex items-center gap-2 mb-1">
                  <s.icon className={`h-4 w-4 ${s.color}`} />
                  <span className="text-xs text-muted-foreground">{s.label}</span>
                </div>
                <p className="text-xl font-bold">{s.value}</p>
              </Card>
            ))}
          </div>

          {/* Charts Row */}
          <div className="grid lg:grid-cols-2 gap-4 mb-6">
            <Card className="p-4 shadow-card">
              <h3 className="font-semibold text-sm mb-3">Orders</h3>
              {orders.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No orders yet</p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={ordersByBucket}>
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="orders" fill="hsl(24,95%,53%)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card className="p-4 shadow-card">
              <h3 className="font-semibold text-sm mb-3">Revenue</h3>
              {orders.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No revenue data yet</p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={revenueByBucket}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => [`₹${v}`, "Revenue"]} />
                    <Line type="monotone" dataKey="revenue" stroke="hsl(24,95%,53%)" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <Card className="p-4 shadow-card">
              <h3 className="font-semibold text-sm mb-3">Top Ordered Items</h3>
              {topItems.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No order data yet</p>
              ) : (
                <div className="space-y-2">
                  {topItems.map((item, i) => (
                    <div key={item.name} className="flex items-center gap-3">
                      <span className="text-xs font-bold text-muted-foreground w-5">{i + 1}</span>
                      <div className="flex-1">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium truncate">{item.name}</span>
                          <span className="text-muted-foreground">{item.count} orders</span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full mt-1 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${(item.count / topItems[0].count) * 100}%`,
                              backgroundColor: COLORS[i % COLORS.length],
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="p-4 shadow-card">
              <h3 className="font-semibold text-sm mb-3">Order Status</h3>
              {statusData.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No orders yet</p>
              ) : (
                <div className="flex items-center gap-4">
                  <ResponsiveContainer width="50%" height={160}>
                    <PieChart>
                      <Pie data={statusData} dataKey="value" cx="50%" cy="50%" outerRadius={60} innerRadius={35}>
                        {statusData.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-1.5">
                    {statusData.map((s, i) => (
                      <div key={s.name} className="flex items-center gap-2 text-xs">
                        <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                        <span>{s.name}: {s.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
