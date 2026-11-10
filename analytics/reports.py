"""Report files (CSV, Excel, PDF) built from the same restaurant-scoped data as the analytics screens."""
import csv
import io
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from .services import item_ranking, money, revenue_orders, window

MIME = {"csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "pdf": "application/pdf"}


def _t(dt):
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M") if dt else ""


def _orders(request, r, d):
    qs, start, end = window(request, r, d)
    if d.get("payment_method"):
        qs = qs.filter(payment_method=d.get("payment_method"))
    if d.get("customer_id"):
        qs = qs.filter(customer_id=d.get("customer_id"))
    if d.get("coupon_code"):
        qs = qs.filter(coupon_code__iexact=d.get("coupon_code"))
    if d.get("menu_item_id"):
        qs = qs.filter(items__food_item_id=d.get("menu_item_id")).distinct()
    if d.get("category_id"):
        qs = qs.filter(items__food_item__category_id=d.get("category_id")).distinct()
    if d.get("delivery_partner_id"):
        qs = qs.filter(delivery_assignments__partner_id=d.get("delivery_partner_id")).distinct()
    return list(qs.select_related("branch").prefetch_related("items").order_by("created_at")), start, end


def rows(request, r, kind, d):
    """(title, header, rows)."""
    orders, start, end = _orders(request, r, d)
    ids = [o.id for o in orders]
    if kind == "orders":
        return "Orders", ["Order", "Date", "Branch", "Type", "Status", "Customer", "Phone", "Items", "Payment", "Paid", "Total"], [
            [o.order_number, _t(o.created_at), o.branch.name, o.order_type, o.status, o.customer_name, o.customer_phone,
             ", ".join(f"{i.quantity}× {i.name}" for i in o.items.all()), o.payment_method, o.payment_status, money(o.total)] for o in orders]
    if kind == "sales":
        day = defaultdict(lambda: [0, Decimal("0"), Decimal("0"), Decimal("0")])
        for o in revenue_orders(orders):
            k = timezone.localtime(o.created_at).date().isoformat()
            day[k][0] += 1
            day[k][1] += o.subtotal
            day[k][2] += o.discount_amount + o.online_discount
            day[k][3] += o.total
        return "Sales by day", ["Date", "Orders", "Item sales", "Discounts", "Total"], [
            [k, v[0], money(v[1]), money(v[2]), money(v[3])] for k, v in sorted(day.items())]
    if kind == "tax":
        return "Tax collected", ["Order", "Date", "Taxable", "Tax", "Total"], [
            [o.order_number, _t(o.created_at), money(o.subtotal - o.discount_amount - o.online_discount), money(o.tax_amount), money(o.total)]
            for o in revenue_orders(orders) if o.tax_amount]
    if kind in ("payments", "refunds"):
        from payments.models import Payment, Refund
        if kind == "payments":
            ps = Payment.objects.filter(order_id__in=ids).select_related("order").order_by("created_at")
            return "Payments", ["Transaction", "Order", "Date", "Gateway", "Method", "Status", "Amount", "Refunded"], [
                [p.transaction_id, p.order.order_number, _t(p.created_at), p.gateway, p.method, p.status, money(p.amount), money(p.refunded_amount)]
                for p in ps]
        fs = Refund.objects.filter(payment__order_id__in=ids).select_related("payment__order").order_by("created_at")
        return "Refunds", ["Order", "Date", "Amount", "Status", "Reason", "By"], [
            [f.payment.order.order_number, _t(f.created_at), money(f.amount), f.status, f.reason, f.created_by] for f in fs]
    if kind == "customers":
        agg = {}
        for o in revenue_orders(orders):
            k = o.customer_id or o.customer_phone or o.customer_name
            if not k:
                continue
            a = agg.setdefault(k, [o.customer_name, o.customer_phone, o.customer_email, 0, Decimal("0"), o.created_at])
            a[3] += 1
            a[4] += o.total
            a[5] = o.created_at
        return "Customers", ["Name", "Phone", "Email", "Orders", "Spend", "Last order"], [
            [a[0], a[1], a[2], a[3], money(a[4]), _t(a[5])] for a in sorted(agg.values(), key=lambda a: -a[4])]
    if kind == "delivery":
        from delivery.models import DeliveryAssignment
        ts = DeliveryAssignment.objects.filter(order_id__in=ids).select_related("order", "partner").order_by("assigned_at")
        return "Deliveries", ["Order", "Rider", "Assigned", "Started", "Delivered", "Status", "Distance km", "Delivery charge"], [
            [t.order.order_number, t.partner.full_name, _t(t.assigned_at), _t(t.started_at), _t(t.delivered_at), t.status,
             float(t.order.delivery_distance_km or 0), money(t.order.delivery_charge)] for t in ts]
    if kind == "staff":
        from staff.models import Attendance
        att = Attendance.objects.filter(staff__restaurant=r, clock_in__gte=start, clock_in__lte=end).select_related("staff")
        if d.get("staff_id"):
            att = att.filter(staff_id=d.get("staff_id"))
        return "Staff attendance", ["Staff", "Role", "Date", "Clock in", "Clock out", "Hours"], [
            [f"{a.staff.first_name} {a.staff.last_name}".strip(), a.staff.role, a.attendance_date.isoformat(), _t(a.clock_in), _t(a.clock_out),
             round(((a.clock_out or timezone.now()) - a.clock_in).total_seconds() / 3600, 2)] for a in att.order_by("clock_in")]
    if kind == "coupons":
        from coupons.models import CouponRedemption
        rs = CouponRedemption.objects.filter(order_id__in=ids).select_related("coupon", "order").order_by("created_at")
        return "Coupon redemptions", ["Code", "Order", "Date", "Customer email", "Discount", "Order total"], [
            [x.coupon.code, x.order.order_number, _t(x.created_at), x.email, money(x.discount), money(x.order.total)] for x in rs]
    if kind == "menu":
        return "Menu performance", ["Item", "Quantity", "Revenue", "Share %"], [
            [i["name"], i["quantity"], i["revenue"], i["share_percent"]] for i in item_ranking(revenue_orders(orders), limit=500)]
    raise ValueError(kind)


def render(fmt, title, header, data, restaurant, start_end=""):
    if fmt == "csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(header)
        w.writerows(data)
        return ("\ufeff" + out.getvalue()).encode("utf-8")
    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = title[:31]
        ws.append(header)
        for row in data:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), title=title, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    cell = styles["BodyText"].clone("cell", fontSize=7.5, leading=9)
    table = Table([[Paragraph(f"<b>{h}</b>", cell) for h in header]] +
                  [[Paragraph(str(v).replace("&", "&amp;").replace("<", "&lt;"), cell) for v in row] for row in data] or [[""]],
                  repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FDE7D6")),
                               ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story = [Paragraph(f"{restaurant.name} — {title}", styles["Title"]), Paragraph(start_end, styles["Normal"]), Spacer(1, 8),
             table if data else Paragraph("No records in this period.", styles["Normal"])]
    doc.build(story)
    return buf.getvalue()


def build(request, restaurant, kind, fmt, data):
    title, header, body = rows(request, restaurant, kind, data)
    _, start, end = window(request, restaurant, data)
    span = f"{timezone.localtime(start):%d %b %Y} – {timezone.localtime(end):%d %b %Y}"
    return render(fmt, title, header, body, restaurant, span), MIME[fmt]
