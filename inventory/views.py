"""Owner inventory screens: ingredients with per-branch stock, adjustments, purchases, history, held stock, recipes."""
from datetime import datetime, time
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsOwnerOrRole
from common.tenancy import get_branch, get_restaurant
from menu.models import FoodItem
from restaurants.models import Branch

from .models import Ingredient, Purchase, Recipe, RecipeLine, StockLevel, StockMovement, StockReservation
from .services import adjust, level_for, q3, recipe_portions, record, stock_status

ROLES = ["manager", "chef", "kitchen", "inventory_manager"]
REASONS = {"restock", "waste", "correction", "consumed", "other"}
KIND_REASON = {"reserve": "reserved", "release": "released", "deduct": "consumed", "purchase": "restock", "opening": "correction"}


def _num(v):
    return float(v) if v is not None else None


def _dec(v, field, *, positive=False, allow_zero=True, places=Decimal("0.001")):
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({field: ["Enter a number."]})
    if not d.is_finite():
        raise ValidationError({field: ["Enter a number."]})
    if positive and (d < 0 or (d == 0 and not allow_zero)):
        raise ValidationError({field: ["Must be more than zero." if not allow_zero else "Can't be negative."]})
    return d.quantize(places)


def _who(request):
    u = request.user
    return (u.get_full_name() or u.username or "")[:150]


def _branch_or_all(request, restaurant):
    raw = request.query_params.get("branch")
    return None if raw in (None, "", "all") else get_branch(request, restaurant)


def ingredient_out(i, branch, linked=None):
    lvl = next((l for l in i.levels.all() if l.branch_id == branch.id), None) if hasattr(i, "_prefetched_objects_cache") and "levels" in i._prefetched_objects_cache else StockLevel.objects.filter(ingredient=i, branch=branch).first()
    if lvl is None:
        lvl = StockLevel(ingredient=i, branch=branch)
    if linked is None:
        linked = list(RecipeLine.objects.filter(ingredient=i).values_list("recipe__food_item_id", flat=True))
    return {"id": i.id, "name": i.name, "unit": i.unit, "unit_cost": float(i.unit_cost), "sku": i.sku,
            "low_stock_threshold": float(i.low_stock_threshold), "stock": float(lvl.on_hand), "reserved": float(lvl.reserved),
            "available": float(lvl.on_hand - lvl.reserved), "status": stock_status(lvl, i.low_stock_threshold),
            "branch_id": branch.id, "branch_name": branch.name, "updated_at": i.updated_at, "linked_menu_item_ids": linked}


def _apply(i, d):
    if "name" in d:
        name = str(d.get("name") or "").strip()[:120]
        if not name:
            raise ValidationError({"name": ["Name is required."]})
        clash = Ingredient.objects.filter(restaurant=i.restaurant, name__iexact=name).exclude(pk=i.pk).exists()
        if clash:
            raise ValidationError({"name": ["An ingredient with this name already exists."]})
        i.name = name
    if "unit" in d:
        unit = str(d.get("unit") or "").strip()[:20]
        if not unit:
            raise ValidationError({"unit": ["Unit is required."]})
        i.unit = unit
    if "low_stock_threshold" in d:
        i.low_stock_threshold = _dec(d.get("low_stock_threshold") or 0, "low_stock_threshold", positive=True)
    if "unit_cost" in d:
        i.unit_cost = _dec(d.get("unit_cost") or 0, "unit_cost", positive=True, places=Decimal("0.01"))
    if "sku" in d:
        i.sku = str(d.get("sku") or "").strip()[:60]


class IngredientList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response([])
        branch = get_branch(request, r)
        links = {}
        for ing_id, fid in RecipeLine.objects.filter(recipe__restaurant=r).values_list("ingredient_id", "recipe__food_item_id"):
            links.setdefault(ing_id, []).append(fid)
        qs = Ingredient.objects.filter(restaurant=r).prefetch_related(Prefetch("levels", queryset=StockLevel.objects.filter(branch=branch)))
        return Response([ingredient_out(i, branch, links.get(i.id, [])) for i in qs])

    def post(self, request):
        r = get_restaurant(request)
        branch = get_branch(request, r)
        d = request.data
        for f in ("name", "unit"):
            if not str(d.get(f) or "").strip():
                raise ValidationError({f: [f"{f.capitalize()} is required."]})
        opening = _dec(d.get("stock") or 0, "stock")
        if opening < 0:
            raise ValidationError({"stock": ["Opening stock can't be negative."]})
        i = Ingredient(restaurant=r)
        _apply(i, {"name": d.get("name"), "unit": d.get("unit"), **{k: d[k] for k in ("low_stock_threshold", "unit_cost", "sku") if k in d}})
        with transaction.atomic():
            i.save()
            StockLevel.objects.bulk_create([StockLevel(ingredient=i, branch=b, on_hand=opening if b.id == branch.id else 0)
                                            for b in r.branches.all()])
            if opening > 0:
                record(StockLevel.objects.get(ingredient=i, branch=branch), StockMovement.Kind.OPENING, opening,
                       reason="correction", note="Opening stock", user=_who(request))
        return Response(ingredient_out(i, branch, []), status=201)


class IngredientDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def _get(self, request, pk):
        r = get_restaurant(request)
        return r, get_object_or_404(Ingredient, pk=pk, restaurant=r)

    def get(self, request, pk):
        r, i = self._get(request, pk)
        return Response(ingredient_out(i, get_branch(request, r)))

    def patch(self, request, pk):
        """Details only. Stock changes go through adjust/purchase so the history stays complete."""
        r, i = self._get(request, pk)
        _apply(i, request.data)
        i.save()
        return Response(ingredient_out(i, get_branch(request, r)))

    put = patch

    def delete(self, request, pk):
        r, i = self._get(request, pk)
        names = list(FoodItem.objects.filter(recipe__lines__ingredient=i).values_list("name", flat=True).distinct())
        if names:
            raise ValidationError({"detail": f"Used in {len(names)} recipe(s): {', '.join(names)}. Remove it from those recipes first."})
        if StockLevel.objects.filter(ingredient=i, reserved__gt=0).exists():
            raise ValidationError({"detail": "Stock is held for open orders."})
        i.delete()
        return Response(status=204)


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def adjust_stock(request, pk):
    r = get_restaurant(request)
    i = get_object_or_404(Ingredient, pk=pk, restaurant=r)
    branch = get_branch(request, r)
    d = request.data
    delta = _dec(d.get("delta"), "delta") if d.get("delta") not in (None, "") else Decimal(0)
    if delta == 0:
        raise ValidationError({"delta": ["Enter a quantity other than zero."]})
    reason = str(d.get("reason") or "correction").strip().lower()
    if reason not in REASONS:
        raise ValidationError({"reason": ["Pick restock, waste, correction, used outside orders or other."]})
    note = str(d.get("note") or "").strip()
    if reason == "other" and not note:
        raise ValidationError({"note": ["Add a note for 'other' adjustments."]})
    if reason == "restock" and delta < 0:
        raise ValidationError({"delta": ["A restock adds stock."]})
    if reason in ("waste", "consumed") and delta > 0:
        raise ValidationError({"delta": ["Waste and use outside orders remove stock."]})
    adjust(i, branch, delta, reason, note, _who(request))
    return Response(ingredient_out(i, branch))


adjust_stock.cls.allowed_roles = ROLES


def purchase_out(p):
    return {"id": p.id, "ingredient_id": p.ingredient_id, "ingredient_name": p.ingredient.name if p.ingredient else p.ingredient_name,
            "branch_id": p.branch_id, "branch_name": p.branch.name, "quantity": float(p.quantity), "unit_cost": float(p.unit_cost),
            "total_cost": float(p.total_cost), "supplier": p.supplier, "invoice_no": p.invoice_no, "purchased_at": p.purchased_at}


def _when(v):
    if v in (None, ""):
        return timezone.now()
    dt = parse_datetime(str(v))
    if dt is None:
        day = parse_date(str(v))
        if day is None:
            raise ValidationError({"purchased_at": ["Enter a valid date."]})
        dt = datetime.combine(day, time(12, 0))
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    if dt > timezone.now() + timezone.timedelta(days=1):
        raise ValidationError({"purchased_at": ["The purchase date can't be in the future."]})
    return dt


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def record_purchase(request, pk):
    r = get_restaurant(request)
    i = get_object_or_404(Ingredient, pk=pk, restaurant=r)
    branch = get_branch(request, r)
    d = request.data
    errors = {}
    try:
        qty = _dec(d.get("quantity"), "quantity")
        if qty <= 0:
            errors["quantity"] = ["Quantity must be more than zero."]
    except ValidationError:
        errors["quantity"] = ["Quantity must be more than zero."]
    try:
        cost = _dec(d.get("unit_cost"), "unit_cost", places=Decimal("0.01"))
        if cost < 0:
            errors["unit_cost"] = ["Enter the cost per unit."]
    except ValidationError:
        errors["unit_cost"] = ["Enter the cost per unit."]
    if errors:
        raise ValidationError(errors)
    when = _when(d.get("purchased_at"))
    supplier = str(d.get("supplier") or "").strip()[:120]
    invoice = str(d.get("invoice_no") or "").strip()[:60]
    with transaction.atomic():
        lvl = level_for(i, branch, lock=True)
        lvl.on_hand = q3(lvl.on_hand + qty)
        lvl.save(update_fields=["on_hand"])
        i.unit_cost = cost
        i.save(update_fields=["unit_cost", "updated_at"])
        p = Purchase.objects.create(restaurant=r, ingredient=i, ingredient_name=i.name, branch=branch, quantity=qty, unit_cost=cost,
                                    total_cost=(qty * cost).quantize(Decimal("0.01")), supplier=supplier, invoice_no=invoice,
                                    purchased_at=when, created_by=request.user)
        note = " · ".join(x for x in (supplier, f"Inv {invoice}" if invoice else "") if x) or "Purchase"
        record(lvl, StockMovement.Kind.PURCHASE, qty, reason="restock", note=note, user=_who(request))
    return Response(purchase_out(p), status=201)


record_purchase.cls.allowed_roles = ROLES


def movement_out(m):
    return {"id": m.id, "ingredient_id": m.ingredient_id, "ingredient_name": m.ingredient.name if m.ingredient else m.ingredient_name,
            "unit": m.unit, "branch_id": m.branch_id, "branch_name": m.branch.name, "delta": float(m.delta), "kind": m.kind,
            "reason": m.reason if m.kind == "adjustment" else KIND_REASON.get(m.kind, m.kind), "note": m.note, "user": m.user,
            "order_id": m.order_id, "order_number": m.order.order_number if m.order_id and m.order else None,
            "on_hand_after": float(m.on_hand_after), "reserved_after": float(m.reserved_after), "created_at": m.created_at}


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def history(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    qs = StockMovement.objects.filter(restaurant=r).select_related("branch", "ingredient", "order")
    branch = _branch_or_all(request, r)
    if branch:
        qs = qs.filter(branch=branch)
    q = request.query_params
    if q.get("ingredient_id"):
        qs = qs.filter(ingredient_id=q.get("ingredient_id"))
    if q.get("kind"):
        qs = qs.filter(kind=q.get("kind"))
    return Response([movement_out(m) for m in qs[:300]])


history.cls.allowed_roles = ROLES


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def purchases(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    qs = Purchase.objects.filter(restaurant=r).select_related("branch", "ingredient")
    branch = _branch_or_all(request, r)
    if branch:
        qs = qs.filter(branch=branch)
    if request.query_params.get("ingredient_id"):
        qs = qs.filter(ingredient_id=request.query_params.get("ingredient_id"))
    return Response([purchase_out(p) for p in qs[:300]])


purchases.cls.allowed_roles = ROLES


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def reservations(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    qs = StockReservation.objects.filter(order__restaurant=r, state="reserved").select_related("order", "branch")
    branch = _branch_or_all(request, r)
    if branch:
        qs = qs.filter(branch=branch)
    ings = {i.id: i for i in Ingredient.objects.filter(restaurant=r)}
    out = []
    for res in qs:
        out.append({"order_id": res.order_id, "order_number": res.order.order_number, "order_status": res.order.status,
                    "branch_id": res.branch_id, "branch_name": res.branch.name, "state": res.state,
                    "lines": [{"ingredient_id": l["ingredient_id"], "ingredient_name": getattr(ings.get(l["ingredient_id"]), "name", "Deleted ingredient"),
                               "unit": getattr(ings.get(l["ingredient_id"]), "unit", ""), "quantity": float(l["quantity"])} for l in res.lines]})
    return Response(out)


reservations.cls.allowed_roles = ROLES


# ─── Recipes ──────────────────────────────────────────────────────────────

def recipe_out(rec, branch):
    lines = list(rec.lines.all())
    return {"id": rec.id, "food_item": rec.food_item_id, "food_item_name": rec.food_item.name, "version": rec.version,
            "updated_at": rec.updated_at,
            "lines": [{"id": l.id, "inventory_item": l.ingredient_id, "inventory_item_name": l.ingredient.name,
                       "quantity": float(l.quantity), "unit": l.ingredient.unit} for l in lines],
            "cost_per_portion": float(sum((l.quantity * l.ingredient.unit_cost for l in lines), Decimal(0)).quantize(Decimal("0.01"))),
            "portions_available": recipe_portions(rec, branch)}


def _recipes(r):
    return (Recipe.objects.filter(restaurant=r).select_related("food_item")
            .prefetch_related(Prefetch("lines", queryset=RecipeLine.objects.select_related("ingredient"))))


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def recipe_list(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    branch = get_branch(request, r)
    return Response([recipe_out(x, branch) for x in _recipes(r)])


recipe_list.cls.allowed_roles = ROLES


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsOwnerOrRole])
def recipe_detail(request, food_item_id):
    """Keyed by the menu item id: PUT creates or replaces that dish's recipe."""
    r = get_restaurant(request)
    food = FoodItem.objects.filter(pk=food_item_id, restaurant=r).first()
    if food is None:
        # 400, not 404: the website treats 404 as "feature not on the server yet".
        raise ValidationError({"detail": "Menu item not found."})
    branch = get_branch(request, r)
    rec = Recipe.objects.filter(food_item=food).first()
    if request.method == "GET":
        if rec is None:
            raise NotFound("This dish has no recipe yet.")
        return Response(recipe_out(_recipes(r).get(pk=rec.pk), branch))
    if request.method == "DELETE":
        if rec is not None:
            rec.delete()
        return Response(status=204)
    lines = request.data.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValidationError({"lines": ["Add at least one ingredient."]})
    ings = {i.id: i for i in Ingredient.objects.filter(restaurant=r)}
    clean, seen = [], set()
    for l in lines:
        if not isinstance(l, dict):
            raise ValidationError({"lines": ["Pick an ingredient for every line."]})
        try:
            ing = ings.get(int(l.get("inventory_item")))
        except (TypeError, ValueError):
            ing = None
        if ing is None:
            raise ValidationError({"lines": ["Pick an ingredient for every line."]})
        if ing.id in seen:
            raise ValidationError({"lines": [f"{ing.name} is listed twice."]})
        seen.add(ing.id)
        try:
            qty = Decimal(str(l.get("quantity"))).quantize(Decimal("0.001"))
        except (InvalidOperation, TypeError, ValueError):
            qty = Decimal(0)
        if not qty.is_finite() or qty <= 0:
            raise ValidationError({"lines": [f"Enter a quantity for {ing.name}."]})
        clean.append((ing, qty))
    with transaction.atomic():
        if rec is None:
            try:
                rec = Recipe.objects.create(restaurant=r, food_item=food)
            except IntegrityError:
                rec = Recipe.objects.get(food_item=food)
        else:
            rec.version += 1
            rec.save(update_fields=["version", "updated_at"])
        # Open orders keep what they already reserved; the new recipe applies to new confirmations.
        rec.lines.all().delete()
        RecipeLine.objects.bulk_create([RecipeLine(recipe=rec, ingredient=i, quantity=q) for i, q in clean])
    return Response(recipe_out(_recipes(r).get(pk=rec.pk), branch))


recipe_detail.cls.allowed_roles = ROLES
