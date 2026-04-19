import { useState } from "react";
import { toast } from "sonner";
import { Link, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { QrCode, Plus, Trash2, ExternalLink, Download, Sparkles, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { useRestaurantProfile, useTables, useCreateTable, useDeleteTable } from "@/hooks/useRestaurantData";
import { isUnlimitedLimit, useCanAddTable, useSubscription } from "@/hooks/useSubscription";
import StyledQRCode, { downloadStyledQR, type QRStyle } from "./StyledQRCode";

const PUBLISHED_URL = "https://zenqrmenu.lovable.app";

const QR_STYLES: { key: QRStyle; label: string; desc: string }[] = [
  { key: "minimal", label: "Minimal", desc: "Clean & simple" },
  { key: "dark", label: "Dark", desc: "Sleek dark mode" },
  { key: "instagram", label: "Cool", desc: "Gradient vibes" },
  { key: "gold", label: "Vibrant", desc: "Luxury feel" },
];

const getCardStyle = (style: QRStyle) => {
  switch (style) {
    case "minimal":
      return "bg-[#FFF7ED] border-primary/20 shadow-card text-[#9A3412]";
    case "dark":
      return "bg-[#0C0A1A] border-[#1E1B3A] text-[#E0E7FF] shadow-[0_0_20px_rgba(56,189,248,0.08)]";
    case "instagram":
      return "bg-gradient-to-br from-[#f9ce34] via-[#ee2a7b] to-[#6228d7] border-none shadow-lg text-white";
    case "gold":
      return "bg-[#111111] border-[#FFD700]/30 shadow-[0_0_40px_rgba(255,215,0,0.1)] text-[#FFF8DC]";
  }
};

const getQRWrapper = (style: QRStyle) => {
  switch (style) {
    case "minimal":
      return "bg-white rounded-2xl p-3 shadow-sm";
    case "dark":
      return "bg-[#0C0A1A] rounded-2xl p-3 ring-1 ring-[#38BDF8]/10";
    case "instagram":
      return "bg-white rounded-2xl p-3 shadow-inner";
    case "gold":
      return "bg-[#111111] rounded-2xl p-3 ring-1 ring-[#FFD700]/20";
  }
};

const getStylePreviewClass = (style: QRStyle, isActive: boolean) => {
  const base = "relative flex flex-col items-center gap-1.5 px-4 py-3 rounded-xl cursor-pointer border-2 transition-all duration-200 ";
  const active = isActive ? "ring-2 ring-primary ring-offset-2 scale-[1.03] " : "hover:scale-[1.02] ";
  switch (style) {
    case "minimal":
      return base + active + (isActive ? "border-primary bg-[#FFF7ED]" : "border-primary/20 bg-[#FFF7ED]/60");
    case "dark":
      return base + active + (isActive ? "border-[#38BDF8] bg-[#0C0A1A] text-[#E0E7FF]" : "border-[#1E1B3A] bg-[#0C0A1A] text-[#94A3B8]");
    case "instagram":
      return base + active + (isActive ? "border-primary bg-gradient-to-br from-[#f9ce34] via-[#ee2a7b] to-[#6228d7] text-white" : "border-[#ee2a7b]/30 bg-gradient-to-br from-[#f9ce34]/20 via-[#ee2a7b]/20 to-[#6228d7]/20 text-foreground");
    case "gold":
      return base + active + (isActive ? "border-[#FFD700] bg-[#111111] text-[#FFF8DC]" : "border-[#FFD700]/20 bg-[#111111]/80 text-[#FFD700]/50");
  }
};

const getSubtextClass = (style: QRStyle) => {
  switch (style) {
    case "minimal": return "text-[#EA580C]/60";
    case "dark": return "text-[#64748b]";
    case "instagram": return "text-white/70";
    case "gold": return "text-[#FFD700]/50";
  }
};

const getDeleteClass = (style: QRStyle) => {
  switch (style) {
    case "dark": return "text-red-400 hover:text-red-300";
    case "instagram": return "text-white/80 hover:text-white";
    case "gold": return "text-red-400 hover:text-red-300";
    default: return "text-destructive";
  }
};

const QRManager = () => {
  const [qrStyle, setQrStyle] = useState<QRStyle>("minimal");
  const [showLimitDialog, setShowLimitDialog] = useState(false);
  const [limitMessage, setLimitMessage] = useState("");
  const navigate = useNavigate();
  const { data: profile } = useRestaurantProfile();
  const { data: fetchedTables, isLoading: tablesLoading, isError: tablesError } = useTables();
  const createTableMutation = useCreateTable();
  const deleteTableMutation = useDeleteTable();

  const allTables = fetchedTables ?? [];
  const { data: subscription } = useSubscription();
  const tableLimit = subscription?.table_limit ?? 0;
  const hasLimit = !!subscription?.is_active && !isUnlimitedLimit(tableLimit) && tableLimit > 0;
  // Only show tables up to the current plan's limit
  const tables = hasLimit ? allTables.slice(0, tableLimit) : allTables;
  const { allowed: canAdd, limit: canAddLimit, reason: tableGateReason } = useCanAddTable(tables.length);
  const showTableUsage = hasLimit;

  const restaurantId = profile?.slug || profile?.id?.toString() || "";
  const restaurantName = profile?.name || "Restaurant";

  const getMenuUrl = (tableId: number) =>
    `${PUBLISHED_URL}/menu/${tableId}`;

  const handleDownload = (tableId: number, tableNumber: string) => {
    downloadStyledQR(
      getMenuUrl(tableId),
      qrStyle,
      `${restaurantName}-table-${tableNumber}-${qrStyle}-qr`
    );
  };

  const firstTableId = tables.length > 0 ? tables[0].id : null;

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <h1 className="text-xl sm:text-2xl font-bold font-heading">Generate QR Codes</h1>
        <div className="flex gap-2">
          {restaurantId && firstTableId && (
            <Link to={`/menu/${firstTableId}`} target="_blank">
              <Button variant="outline" size="sm">
                <ExternalLink className="h-4 w-4 mr-1" /> Preview
              </Button>
            </Link>
          )}
          <Button
            variant="hero"
            size="sm"
            disabled={createTableMutation.isPending}
            onClick={() => {
              if (!canAdd) {
                setLimitMessage(tableGateReason || `You've reached your limit of ${isUnlimitedLimit(canAddLimit) ? tables.length : canAddLimit} tables on your current plan.`);
                setShowLimitDialog(true);
                return;
              }
              const maxNum = allTables.reduce((max, t) => Math.max(max, Number(t.table_number) || 0), 0);
              createTableMutation.mutate(maxNum + 1, {
                onError: (error: any) => {
                  const msg = String(error?.message || "");
                  const displayLimit = isUnlimitedLimit(canAddLimit) ? tables.length : canAddLimit;
                  setLimitMessage(msg || `You've reached your limit of ${displayLimit} tables. Upgrade to add more.`);
                  setShowLimitDialog(true);
                },
              });
            }}
          >
            {createTableMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Plus className="h-4 w-4 mr-1" />
            )}
            Add Table {showTableUsage ? `(${tables.length}/${canAddLimit})` : ""}
          </Button>
        </div>
      </div>

      {!restaurantId && (
        <Card className="p-5 mb-6 border-destructive/20 bg-destructive/5">
          <p className="text-sm text-muted-foreground">
            Please set up your restaurant profile first in the <strong>Restaurant</strong> tab so QR codes can link to your menu.
          </p>
        </Card>
      )}

      {/* Style Picker */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
          <Sparkles className="h-4 w-4 text-primary" /> Choose QR Style
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {QR_STYLES.map((s) => (
            <button
              key={s.key}
              onClick={() => setQrStyle(s.key)}
              className={getStylePreviewClass(s.key, qrStyle === s.key)}
            >
              <div className={getQRWrapper(s.key) + " mb-1 overflow-hidden"}>
                <StyledQRCode
                  value="https://zenqrmenu.lovable.app"
                  size={48}
                  style={s.key}
                />
              </div>
              <span className="text-xs font-semibold">{s.label}</span>
              <span className="text-[10px] opacity-60">{s.desc}</span>
            </button>
          ))}
        </div>
      </div>


      {tablesLoading && !tablesError && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-muted-foreground">Loading tables...</span>
        </div>
      )}

      {(tablesError || (!tablesLoading && tables.length === 0)) && (
        <Card className="p-5 mb-6 border-muted">
          <p className="text-sm text-muted-foreground">
            {tablesError
              ? "Could not load tables from backend. Use the Add Table button to create QR codes manually."
              : "No tables found. Click Add Table to create QR codes."}
          </p>
        </Card>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
        {tables?.map((table) => (
          <Card key={table.id} className={"p-4 sm:p-6 text-center transition-all " + getCardStyle(qrStyle)}>
            <div className={"mx-auto h-28 w-28 sm:h-36 sm:w-36 flex items-center justify-center mb-3 sm:mb-4 overflow-hidden " + getQRWrapper(qrStyle)}>
              {restaurantId ? (
                <StyledQRCode
                  value={getMenuUrl(table.id)}
                  size={120}
                  style={qrStyle}
                />
              ) : (
                <QrCode className="h-20 w-20 text-muted-foreground" />
              )}
            </div>
            <h3 className="font-semibold mb-1">Table {table.table_number}</h3>
            <p className={"text-xs mb-4 " + getSubtextClass(qrStyle)}>Scan to view menu</p>
            <div className="flex gap-2">
              {restaurantId && (
                <>
                  <Link to={`/menu/${table.id}`} target="_blank" className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">Preview</Button>
                  </Link>
                  <Button variant="outline" size="sm" onClick={() => handleDownload(table.id, String(table.table_number))}>
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </>
              )}
              <Button
                variant="outline"
                size="sm"
                className={getDeleteClass(qrStyle)}
                disabled={deleteTableMutation.isPending}
                onClick={() => {
                  if (confirm(`Delete Table ${table.table_number}?`)) {
                    deleteTableMutation.mutate(table.id, {
                      onSuccess: () => toast.success(`Table ${table.table_number} deleted`),
                      onError: (err: any) => toast.error(err?.message || "Failed to delete table"),
                    });
                  }
                }}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* Limit Reached Dialog */}
      <Dialog open={showLimitDialog} onOpenChange={setShowLimitDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <DialogTitle className="text-center text-xl">Table Limit Reached</DialogTitle>
            <DialogDescription className="text-center">
              {limitMessage || "You've reached the table limit on your current plan."}
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-center">
            <p className="text-sm font-medium text-foreground mb-1">
              🚀 Unlock more tables & premium features
            </p>
            <p className="text-xs text-muted-foreground">
              Upgrade your plan to add unlimited tables, get priority support, and access advanced analytics.
            </p>
          </div>
          <DialogFooter className="flex-col gap-2 sm:flex-col">
            <Button variant="hero" className="w-full" onClick={() => { setShowLimitDialog(false); navigate("/pricing"); }}>
              Upgrade Now
            </Button>
            <Button variant="ghost" className="w-full" onClick={() => setShowLimitDialog(false)}>
              Maybe Later
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default QRManager;
