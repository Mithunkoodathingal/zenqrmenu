import { useMemo } from "react";
import { Card } from "@/components/ui/card";
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

const AnalyticsDashboard = () => {
  const { data: orders = [], isLoading: loadingOrders } = useQuery<Order[]>({
    queryKey: ["orders"],
    queryFn: () => fetchOrders(),
    refetchInterval: 30000,
    retry: (c, e) => (e as Error).message !== "LOGIN_REQUIRED" && c < 2,
  });

  const { data: menuItems = [] } = useMenuItems();
  const { data: categories = [] } = useCategories();
  const { data: tables = [] } = useTables();

  const stats = useMemo(() => {
    const totalOrders = orders.length;
    const pending = orders.filter(o => o.status === "pending").length;
    const completed = orders.filter(o => o.status === "completed").length;
    const cancelled = orders.filter(o => o.status === "cancelled").length;
    const totalRevenue = orders
      .filter(o => o.status !== "cancelled")
      .reduce((sum, o) => sum + (o.total_price || 0), 0);

    return { totalOrders, pending, completed, cancelled, totalRevenue };
  }, [orders]);

  // Orders by day (last 7 days)
  const ordersByDay = useMemo(() => {
    const days: Record<string, number> = {};
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const key = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });
      days[key] = 0;
    }
    orders.forEach(o => {
      const d = new Date(o.created_at);
      const key = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });
      if (key in days) days[key]++;
    });
    return Object.entries(days).map(([day, count]) => ({ day, orders: count }));
  }, [orders]);

  // Top ordered items
  const topItems = useMemo(() => {
    const counts: Record<string, number> = {};
    orders.forEach(o => {
      o.items?.forEach(item => {
        const name = item.name || "Unknown";
        counts[name] = (counts[name] || 0) + item.quantity;
      });
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, count]) => ({ name, count }));
  }, [orders]);

  // Orders by status for pie chart
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

  // Revenue by day
  const revenueByDay = useMemo(() => {
    const days: Record<string, number> = {};
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const key = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });
      days[key] = 0;
    }
    orders
      .filter(o => o.status !== "cancelled")
      .forEach(o => {
        const d = new Date(o.created_at);
        const key = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });
        if (key in days) days[key] += o.total_price || 0;
      });
    return Object.entries(days).map(([day, revenue]) => ({ day, revenue: Math.round(revenue) }));
  }, [orders]);

  const isLoading = loadingOrders;

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
      <h1 className="text-2xl font-bold font-heading mb-6">Analytics</h1>

      {isLoading ? (
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
            {/* Orders Trend */}
            <Card className="p-4 shadow-card">
              <h3 className="font-semibold text-sm mb-3">Orders (Last 7 Days)</h3>
              {orders.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No orders yet</p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={ordersByDay}>
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="orders" fill="hsl(24,95%,53%)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* Revenue Trend */}
            <Card className="p-4 shadow-card">
              <h3 className="font-semibold text-sm mb-3">Revenue (Last 7 Days)</h3>
              {orders.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No revenue data yet</p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={revenueByDay}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => [`₹${v}`, "Revenue"]} />
                    <Line type="monotone" dataKey="revenue" stroke="hsl(24,95%,53%)" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            {/* Top Items */}
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

            {/* Order Status Distribution */}
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
