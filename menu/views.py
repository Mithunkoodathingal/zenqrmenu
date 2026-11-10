"""Owner menu tools (categories, items, add-ons, branch overrides), the public table menu, and AI menu import."""
import base64
import json
import logging
import re

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.geo import money
from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant, require_owner
from restaurants.models import Branch, Table
from restaurants.services import is_open_at, media_url

from .models import AddOn, BranchCategoryOverride, BranchItemOverride, Category, FoodItem
from .services import BranchMenu, discount_percent, normalize_pricing

log = logging.getLogger(__name__)
TYPE_KEYS = ["is_veg", "veg", "food_type", "foodType", "food_item_type", "foodItemType", "fooditem_type", "fooditemType", "item_type", "itemType"]
MARKER = re.compile(r"\s*\[\[(veg|non[_-]?veg)\]\]\s*", re.I)


def _bool(v):
    return v is True or str(v).strip().lower() in {"true", "1", "yes", "on"}


def _is_veg(d, current=True):
    for key in TYPE_KEYS:
        if key in d and d[key] not in (None, ""):
            v = d[key]
            if isinstance(v, bool):
                return v
            s = str(v).strip().lower()
            if s in {"true", "1", "veg", "vegetarian"}:
                return True
            if s in {"false", "0", "non_veg", "non-veg", "nonveg", "non veg"}:
                return False
    return current


def category_out(c):
    return {"id": c.id, "name": c.name, "position": c.position}


def item_out(i, request, menu=None):
    price = menu.price(i) if menu else money(i.price)
    _, original = normalize_pricing(price, i.original_price)
    image = media_url(request, i.image, i.image_url)
    out = {
        "id": i.id, "name": i.name, "description": i.description, "category": i.category_id, "category_name": i.category.name,
        "price": float(price), "original_price": float(original) if original else None,
        "discount_percent": discount_percent(price, original), "is_available": i.is_available, "is_paused": not i.is_available,
        "is_veg": i.is_veg, "food_type": "veg" if i.is_veg else "non_veg", "image": image, "image_url": image,
        "addons": [{"id": a.id, "name": a.name, "price": float(a.price)} for a in i.addons.all() if a.is_available],
        "position": i.position,
    }
    from django.apps import apps
    if apps.is_installed("inventory"):
        from inventory.models import Recipe
        out["recipe_id"] = Recipe.objects.filter(food_item=i).values_list("id", flat=True).first()
    return out


# ─── Categories ───────────────────────────────────────────────────────────

class CategoryList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        return Response([category_out(c) for c in r.categories.all()] if r else [])

    def post(self, request):
        r = get_restaurant(request)
        name = str(request.data.get("name", "")).strip()[:100]
        if not name:
            raise ValidationError({"name": ["This field is required."]})
        if r.categories.filter(name__iexact=name).exists():
            raise ValidationError({"name": ["You already have a category with this name."]})
        c = Category.objects.create(restaurant=r, name=name, position=r.categories.count())
        return Response(category_out(c), status=201)


class CategoryDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request, pk):
        return Response(category_out(get_object_or_404(Category, pk=pk, restaurant=get_restaurant(request))))

    def patch(self, request, pk):
        r = get_restaurant(request)
        c = get_object_or_404(Category, pk=pk, restaurant=r)
        if "name" in request.data:
            name = str(request.data.get("name", "")).strip()[:100]
            if not name:
                raise ValidationError({"name": ["This field is required."]})
            if r.categories.filter(name__iexact=name).exclude(pk=c.pk).exists():
                raise ValidationError({"name": ["You already have a category with this name."]})
            c.name = name
        if "position" in request.data:
            c.position = max(0, int(request.data.get("position") or 0))
        c.save()
        return Response(category_out(c))

    put = patch

    def delete(self, request, pk):
        c = get_object_or_404(Category, pk=pk, restaurant=get_restaurant(request))
        c.delete()
        return Response(status=204)


# ─── Items ────────────────────────────────────────────────────────────────

def _addons(raw):
    if raw in (None, ""):
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raise ValidationError({"addons": ["Send add-ons as a list."]})
    if not isinstance(raw, list):
        raise ValidationError({"addons": ["Send add-ons as a list."]})
    out = []
    for a in raw[:30]:
        name = str((a or {}).get("name", "")).strip()[:100]
        if not name:
            continue
        price = money((a or {}).get("price") or 0)
        if price < 0:
            raise ValidationError({"addons": ["Add-on prices can't be negative."]})
        out.append({"id": (a or {}).get("id"), "name": name, "price": price})
    return out


def _apply_item(item, request, creating=False):
    d = request.data
    r = item.restaurant
    errors = {}
    if "name" in d or creating:
        name = str(d.get("name", "")).strip()[:150]
        if not name:
            errors["name"] = ["Enter the item's name."]
        item.name = name
    if "description" in d:
        desc = str(d.get("description") or "")
        item.description = MARKER.sub(" ", desc).strip()
    if "category" in d or creating:
        try:
            item.category = Category.objects.get(pk=int(d.get("category")), restaurant=r)
        except (Category.DoesNotExist, TypeError, ValueError):
            errors["category"] = ["Pick one of your categories."]
    if "price" in d or "original_price" in d or creating:
        raw_price = d.get("price", item.price if not creating else None)
        try:
            price, original = normalize_pricing(raw_price, d.get("original_price", item.original_price))
        except Exception:
            price, original = money(0), None
        if price <= 0:
            errors["price"] = ["Price must be more than zero."]
        item.price, item.original_price = price, original
    if "is_paused" in d:
        item.is_available = not _bool(d["is_paused"])
    elif "is_available" in d:
        item.is_available = _bool(d["is_available"])
    item.is_veg = _is_veg(d, item.is_veg)
    image = request.FILES.get("image")
    if image is not None:
        if image.size > 10 * 1024 * 1024 or not (image.content_type or "").startswith("image/"):
            errors["image"] = ["Upload an image under 10 MB."]
        else:
            item.image, item.image_url = image, ""
    elif "image" in d and isinstance(d.get("image"), str):
        value = d.get("image").strip()
        if value.startswith("http://") or value.startswith("https://"):
            item.image, item.image_url = None, value[:600]
        elif value in ("", "null"):
            item.image, item.image_url = None, ""
    elif "image" in d and d.get("image") is None:
        item.image, item.image_url = None, ""
    if errors:
        raise ValidationError(errors)
    return _addons(d.get("addons")) if "addons" in d else None


def _save_addons(item, addons):
    if addons is None:
        return
    keep = []
    for a in addons:
        obj = item.addons.filter(pk=a["id"]).first() if a.get("id") else None
        if obj:
            obj.name, obj.price, obj.is_available = a["name"], a["price"], True
            obj.save()
        else:
            obj = AddOn.objects.create(food_item=item, name=a["name"], price=a["price"])
        keep.append(obj.pk)
    item.addons.exclude(pk__in=keep).delete()


class ItemList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager", "kitchen", "waiter", "cashier"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response([])
        qs = r.items.select_related("category").prefetch_related("addons")
        return Response([item_out(i, request) for i in qs])

    def post(self, request):
        r = get_restaurant(request)
        from subscriptions.services import check_limit
        check_limit(r, "items")
        item = FoodItem(restaurant=r)
        with transaction.atomic():
            addons = _apply_item(item, request, creating=True)
            item.position = r.items.filter(category=item.category).count()
            item.save()
            _save_addons(item, addons)
        return Response(item_out(item, request), status=201)


class ItemDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request, pk):
        return Response(item_out(get_object_or_404(FoodItem, pk=pk, restaurant=get_restaurant(request)), request))

    def patch(self, request, pk):
        item = get_object_or_404(FoodItem, pk=pk, restaurant=get_restaurant(request))
        with transaction.atomic():
            addons = _apply_item(item, request)
            item.save()
            _save_addons(item, addons)
        return Response(item_out(item, request))

    put = patch

    def delete(self, request, pk):
        item = get_object_or_404(FoodItem, pk=pk, restaurant=get_restaurant(request))
        item.delete()
        return Response(status=204)


# ─── Branch overrides ─────────────────────────────────────────────────────

def _branch(request, pk):
    r = require_owner(request) if request.method != "GET" else get_restaurant(request)
    return get_object_or_404(Branch, pk=pk, restaurant=r)


class ItemOverrides(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request, pk):
        b = _branch(request, pk)
        return Response(self._list(b))

    def put(self, request, pk):
        b = _branch(request, pk)
        d = request.data
        item = get_object_or_404(FoodItem, pk=d.get("food_item") or 0, restaurant=b.restaurant)
        price = d.get("price")
        price = None if price in (None, "") else money(price)
        if price is not None and price <= 0:
            raise ValidationError({"price": ["Price must be more than zero."]})
        hidden = d.get("is_available") is False or str(d.get("is_available")).lower() == "false"
        BranchItemOverride.objects.filter(branch=b, food_item=item).delete()
        if hidden or price is not None:
            BranchItemOverride.objects.create(branch=b, food_item=item, is_available=False if hidden else None, price=price)
        return Response(self._list(b))

    post = put

    @staticmethod
    def _list(b):
        return [{"food_item": o.food_item_id, "branch": b.id, "is_available": o.is_available,
                 "price": float(o.price) if o.price is not None else None} for o in b.item_overrides.all()]


class CategoryOverrides(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request, pk):
        return Response(self._list(_branch(request, pk)))

    def put(self, request, pk):
        b = _branch(request, pk)
        cat = get_object_or_404(Category, pk=request.data.get("category") or 0, restaurant=b.restaurant)
        BranchCategoryOverride.objects.filter(branch=b, category=cat).delete()
        if request.data.get("is_available") is False or str(request.data.get("is_available")).lower() == "false":
            BranchCategoryOverride.objects.create(branch=b, category=cat, is_available=False)
        return Response(self._list(b))

    post = put

    @staticmethod
    def _list(b):
        return [{"category": o.category_id, "branch": b.id, "is_available": o.is_available} for o in b.category_overrides.all()]


# ─── Public table menu ────────────────────────────────────────────────────

def public_menu(table, request):
    r, branch = table.restaurant, table.branch
    menu = BranchMenu(r, branch)
    categories = [category_out(c) for c in r.categories.all() if c.id not in menu.hidden_categories]
    items = []
    for i in r.items.select_related("category").prefetch_related("addons"):
        if i.category_id in menu.hidden_categories:
            continue
        reason = menu.unavailable_reason(i)
        row = item_out(i, request, menu)
        row.update({"is_available": reason is None, "unavailable_reason": reason, "portions_left": menu.portions_left(i)})
        row.pop("recipe_id", None)
        items.append(row)
    from restaurants.services import public_card
    card = public_card(r, request)
    return {
        "restaurant": {**card, "logo_url": card["logo"], "cover_image_url": card["cover_image"]},
        "table": {"id": table.id, "table_number": table.table_number}, "table_number": table.table_number,
        "branch_id": branch.id, "branch_name": branch.name, "is_open": is_open_at(r),
        "categories": categories, "items": items,
    }


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_table_menu(request, pk):
    table = get_object_or_404(Table.objects.select_related("restaurant", "branch"), pk=pk,
                              restaurant__is_active=True, restaurant__deleted_at__isnull=True)
    return Response(public_menu(table, request))


# ─── AI menu import ───────────────────────────────────────────────────────

PROMPT = (
    "Read this restaurant menu and return JSON only: {\"items\": [{\"item_name\": str, \"category\": str, "
    "\"description\": str, \"price\": number|null, \"veg_or_nonveg\": \"veg\"|\"non-veg\", \"confidence\": number 0-1, "
    "\"image_search_term\": str}]}. Use the menu's own section names as categories. Prices are numbers without currency."
)


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def ai_extract(request):
    get_restaurant(request)
    if not settings.GEMINI_API_KEY:
        return Response({"success": False, "detail": "Menu import isn't set up on the server yet."}, status=503)
    f = request.FILES.get("file")
    if f is None:
        raise ValidationError({"file": ["Upload a photo or PDF of your menu."]})
    mime = f.content_type or "application/octet-stream"
    if not (mime.startswith("image/") or mime == "application/pdf") or f.size > 15 * 1024 * 1024:
        raise ValidationError({"file": ["Upload an image or PDF under 15 MB."]})
    body = {"contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": mime, "data": base64.b64encode(f.read()).decode()}}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}}
    try:
        res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
                            params={"key": settings.GEMINI_API_KEY}, json=body, timeout=90)
        res.raise_for_status()
        text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        items = json.loads(text).get("items", [])
    except Exception:
        log.exception("Menu import failed")
        return Response({"success": False, "detail": "Unable to read menu. Please try another image or PDF."}, status=502)
    clean = [i for i in items if isinstance(i, dict) and str(i.get("item_name", "")).strip()]
    return Response({"success": bool(clean), "items": clean[:300]})


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def ai_image_search(request):
    q = (request.query_params.get("q") or "").strip()[:100]
    if not q:
        return Response({"success": False})
    try:
        if settings.UNSPLASH_ACCESS_KEY:
            res = requests.get("https://api.unsplash.com/search/photos", params={"query": f"{q} food", "per_page": 1, "orientation": "squarish"},
                               headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}, timeout=10)
            results = res.json().get("results") or []
            if results:
                return Response({"success": True, "image_url": results[0]["urls"]["small"]})
        if settings.PEXELS_API_KEY:
            res = requests.get("https://api.pexels.com/v1/search", params={"query": f"{q} food", "per_page": 1},
                               headers={"Authorization": settings.PEXELS_API_KEY}, timeout=10)
            photos = res.json().get("photos") or []
            if photos:
                return Response({"success": True, "image_url": photos[0]["src"]["medium"]})
    except Exception:
        log.exception("Image search failed")
    if not settings.UNSPLASH_ACCESS_KEY and not settings.PEXELS_API_KEY:
        return Response({"success": False, "detail": "Image search isn't set up on the server yet."}, status=503)
    return Response({"success": False})


# ─── Dashboard search ─────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def search(request):
    r = get_restaurant(request, required=False)
    q = (request.query_params.get("q") or "").strip()
    if r is None or len(q) < 2:
        return Response([])
    wanted = set(filter(None, (request.query_params.get("entities") or "").split(",")))
    results = []
    if not wanted or "menu_item" in wanted:
        results += [{"entity": "menu_item", "id": i.id, "title": i.name, "subtitle": i.category.name, "url": "/dashboard?tab=menu"}
                    for i in r.items.select_related("category").filter(name__icontains=q)[:8]]
    if not wanted or "table" in wanted:
        results += [{"entity": "table", "id": t.id, "title": f"Table {t.table_number}", "subtitle": t.branch.name, "url": "/dashboard?tab=qr"}
                    for t in r.tables.select_related("branch").filter(table_number__icontains=q)[:5]]
    from django.apps import apps
    for app, fn in (("orders", "orders.search.search_orders"), ("staff", "staff.search.search_staff"), ("delivery", "delivery.search.search_partners")):
        if apps.is_installed(app):
            module, name = fn.rsplit(".", 1)
            results += getattr(__import__(module, fromlist=[name]), name)(r, q, wanted)
    return Response(results[:30])
