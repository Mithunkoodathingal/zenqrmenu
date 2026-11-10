"""Stock rules (same as the website's src/lib/inventoryRules.ts):

- confirmed / preparing / ready → reserve the order's recipe ingredients at its branch (all or nothing)
- completed → deduct: on-hand and reserved both go down (reserving first if it was never confirmed)
- cancelled → release a held reservation; already-used stock is never put back
Available = on hand − reserved. Add-ons don't use stock.
"""
from collections import defaultdict
from decimal import ROUND_FLOOR, Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException

from .models import Ingredient, Recipe, RecipeLine, StockLevel, StockMovement, StockReservation

Q3 = Decimal("0.001")
HOLDING = ("confirmed", "preparing", "ready")


class NotEnoughStock(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Not enough stock."


def q3(v):
    return Decimal(str(v)).quantize(Q3)


def stock_status(level, threshold):
    a = level.on_hand - level.reserved
    if a <= 0:
        return "out_of_stock"
    if a <= threshold:
        return "low_stock"
    return "in_stock"


def init_branch_stock(branch):
    """A new branch starts with zero of every ingredient."""
    StockLevel.objects.bulk_create(
        [StockLevel(ingredient=i, branch=branch) for i in Ingredient.objects.filter(restaurant=branch.restaurant)],
        ignore_conflicts=True,
    )


def level_for(ingredient, branch, lock=False):
    qs = StockLevel.objects.select_for_update() if lock else StockLevel.objects
    lvl, _ = qs.get_or_create(ingredient=ingredient, branch=branch)
    return lvl


def record(level, kind, delta, *, reason="", note="", user="", order=None):
    i = level.ingredient
    return StockMovement.objects.create(
        restaurant_id=i.restaurant_id, ingredient=i, ingredient_name=i.name, unit=i.unit, branch_id=level.branch_id,
        delta=q3(delta), kind=kind, reason=reason, note=note[:255], user=user[:150], order=order,
        on_hand_after=level.on_hand, reserved_after=level.reserved,
    )


def portions_map(restaurant, branch):
    """{food_item_id: portions this branch can still make}; dishes without a recipe are left out (unlimited)."""
    levels = {l.ingredient_id: l.on_hand - l.reserved for l in StockLevel.objects.filter(branch=branch)}
    out = {}
    for line in RecipeLine.objects.filter(recipe__restaurant=restaurant).select_related("recipe"):
        if line.quantity <= 0:
            continue
        n = int(((levels.get(line.ingredient_id, Decimal(0)) / line.quantity)).to_integral_value(rounding=ROUND_FLOOR))
        fid = line.recipe.food_item_id
        out[fid] = max(0, min(out.get(fid, n), n))
    return out


def recipe_portions(recipe, branch):
    lines = list(recipe.lines.all())
    if not lines:
        return None
    levels = {l.ingredient_id: l.on_hand - l.reserved for l in StockLevel.objects.filter(branch=branch)}
    return max(0, min(int((levels.get(l.ingredient_id, Decimal(0)) / l.quantity).to_integral_value(rounding=ROUND_FLOOR))
                      for l in lines if l.quantity > 0))


def order_usage(order):
    """[{ingredient_id, quantity}] = recipe quantity × ordered quantity, summed per ingredient."""
    totals = defaultdict(Decimal)
    items = list(order.items.all())
    recipes = {r.food_item_id: r for r in Recipe.objects.filter(food_item_id__in=[i.food_item_id for i in items if i.food_item_id])
               .prefetch_related("lines")}
    for it in items:
        r = recipes.get(it.food_item_id)
        if not r:
            continue
        for l in r.lines.all():
            totals[l.ingredient_id] += l.quantity * it.quantity
    return [{"ingredient_id": k, "quantity": str(q3(v))} for k, v in sorted(totals.items())]


def _locked_levels(branch, lines):
    ids = [l["ingredient_id"] for l in lines]
    for i in Ingredient.objects.filter(pk__in=ids):
        StockLevel.objects.get_or_create(ingredient=i, branch=branch)
    return {l.ingredient_id: l for l in StockLevel.objects.select_for_update().select_related("ingredient")
            .filter(branch=branch, ingredient_id__in=ids).order_by("ingredient_id")}


def _shortfall_message(branch, lines, levels):
    short = []
    for l in lines:
        lvl = levels.get(l["ingredient_id"])
        need = Decimal(l["quantity"])
        if lvl is None:
            continue
        if lvl.on_hand - lvl.reserved < need:
            short.append(f"{lvl.ingredient.name} needs {_n(need)} {lvl.ingredient.unit}, {_n(lvl.on_hand - lvl.reserved)} available")
    if not short:
        return None
    return f"Not enough stock at {branch.name}: " + "; ".join(short) + ". Record a purchase or adjust stock, then try again."


def _n(d):
    return f"{d.normalize():f}" if d != d.to_integral_value() else str(int(d))


def _reserve(order, lines, levels):
    msg = _shortfall_message(order.branch, lines, levels)
    if msg:
        raise NotEnoughStock(msg)
    for l in lines:
        lvl = levels.get(l["ingredient_id"])
        if lvl is None:
            continue  # ingredient deleted since; nothing to hold
        lvl.reserved = q3(lvl.reserved + Decimal(l["quantity"]))
        lvl.save(update_fields=["reserved"])
        record(lvl, StockMovement.Kind.RESERVE, 0, reason="reserved", user="system", order=order,
               note=f"Held {_n(Decimal(l['quantity']))} for order {order.order_number}")


def on_status_change(order, old, new):
    """Called inside the order's transaction before the new status is saved. Raises 409 on a shortfall."""
    res = StockReservation.objects.select_for_update().filter(order=order).first()
    held = res is not None and res.state == StockReservation.State.RESERVED
    if new in HOLDING:
        if res is not None and res.state != StockReservation.State.RELEASED:
            return
        lines = order_usage(order)
        levels = _locked_levels(order.branch, lines)
        _reserve(order, lines, levels)
        StockReservation.objects.update_or_create(order=order, defaults={"branch": order.branch, "state": "reserved", "lines": lines})
    elif new == "completed":
        if res is not None and res.state == StockReservation.State.DEDUCTED:
            return
        lines = res.lines if held else order_usage(order)
        levels = _locked_levels(order.branch, lines)
        if not held:
            _reserve(order, lines, levels)
        for l in lines:
            lvl = levels.get(l["ingredient_id"])
            if lvl is None:
                continue
            qty = Decimal(l["quantity"])
            lvl.on_hand = q3(lvl.on_hand - qty)
            lvl.reserved = q3(max(Decimal(0), lvl.reserved - qty))
            lvl.save(update_fields=["on_hand", "reserved"])
            record(lvl, StockMovement.Kind.DEDUCT, -qty, reason="consumed", user="system", order=order,
                   note=f"Used {_n(qty)} for order {order.order_number}")
        StockReservation.objects.update_or_create(order=order, defaults={"branch": order.branch, "state": "deducted", "lines": lines})
    elif new == "cancelled" and held:
        levels = _locked_levels(res.branch, res.lines)
        for l in res.lines:
            lvl = levels.get(l["ingredient_id"])
            if lvl is None:
                continue
            qty = Decimal(l["quantity"])
            lvl.reserved = q3(max(Decimal(0), lvl.reserved - qty))
            lvl.save(update_fields=["reserved"])
            record(lvl, StockMovement.Kind.RELEASE, 0, reason="released", user="system", order=order,
                   note=f"Returned {_n(qty)} from order {order.order_number}")
        res.state = StockReservation.State.RELEASED
        res.save(update_fields=["state", "updated_at"])


def stock_state(order):
    res = getattr(order, "stock_reservation", None)
    try:
        if res is not None:
            return res.state
    except StockReservation.DoesNotExist:  # pragma: no cover
        pass
    return "not_reserved" if order_usage(order) else "no_recipe"


@transaction.atomic
def adjust(ingredient, branch, delta, reason, note, user):
    lvl = level_for(ingredient, branch, lock=True)
    nxt = q3(lvl.on_hand + delta)
    if nxt < 0:
        raise_bad(f"Only {_n(lvl.on_hand)} {ingredient.unit} on hand at {branch.name} — can't remove {_n(-delta)}.")
    if nxt < lvl.reserved:
        raise_bad(f"{_n(lvl.reserved)} {ingredient.unit} is held for open orders. You can remove at most "
                  f"{_n(lvl.on_hand - lvl.reserved)} {ingredient.unit}.")
    lvl.on_hand = nxt
    lvl.save(update_fields=["on_hand"])
    record(lvl, StockMovement.Kind.ADJUSTMENT, delta, reason=reason, note=note, user=user)
    return lvl


def raise_bad(msg):
    from rest_framework.exceptions import ValidationError
    raise ValidationError({"detail": msg})
