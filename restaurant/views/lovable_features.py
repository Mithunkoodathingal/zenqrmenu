from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurant.models import DeliveryPartner, FoodItem, Order, Restaurant
from restaurant.services.common import get_restaurant
from restaurant.services.delivery import (
    calculate_distance,
    get_delivery_summary,
    update_delivery_status,
)
from restaurant.services.analytics import (
    get_customer_statistics,
    get_daily_sales,
    get_delivery_statistics,
    get_menu_statistics,
    get_monthly_sales,
    get_order_statistics,
    get_restaurant_statistics,
    get_sales_statistics,
    get_staff_statistics,
    get_top_selling_items,
    get_weekly_sales,
    get_yearly_sales,
)

from restaurant.feature_models import Coupon, CouponRedemption, InventoryItem, Review


def _restaurant_or_404(request):
    restaurant = get_restaurant(request)
    if restaurant is None:
        return None, Response({"success": False, "message": "Restaurant not found."}, status=404)
    return restaurant, None


def _order_payload(order):
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
        "order_type": order.order_type,
        "delivery_status": order.delivery_status,
        "kitchen_printed": order.kitchen_printed,
        "receipt_printed": order.receipt_printed,
        "is_completed": order.is_completed,
        "cancelled_at": getattr(order, "cancelled_at", None),
    }


class OrderCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        order = get_object_or_404(Order, id=order_id, restaurant=restaurant, is_deleted=False)
        if order.is_completed or order.status == "completed":
            return Response({"success": False, "message": "Completed orders cannot be cancelled."}, status=400)
        if order.status == "cancelled":
            return Response({"success": False, "message": "Order is already cancelled."}, status=400)
        if order.payment_status == "refunded":
            return Response({"success": False, "message": "A fully refunded order cannot be cancelled again."}, status=400)

        reason = str(request.data.get("reason", "Cancelled by restaurant")).strip()[:500]
        order.status = "cancelled"
        if order.order_type == "delivery":
            if order.delivery_partner:
                order.delivery_partner.is_available = True
                order.delivery_partner.save(update_fields=["is_available"])
            order.delivery_status = "cancelled"
        order.is_completed = False
        update_fields = ["status", "is_completed"]
        if order.order_type == "delivery":
            update_fields.append("delivery_status")
        order.save(update_fields=update_fields)
        return Response({"success": True, "message": "Order cancelled successfully.", "reason": reason, "order": _order_payload(order)})


class OrderPrintStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        order = get_object_or_404(Order, id=order_id, restaurant=restaurant, is_deleted=False)
        changed = []
        if "kitchen_printed" in request.data:
            order.kitchen_printed = bool(request.data.get("kitchen_printed"))
            changed.append("kitchen_printed")
        if "receipt_printed" in request.data:
            order.receipt_printed = bool(request.data.get("receipt_printed"))
            changed.append("receipt_printed")
        if not changed:
            return Response({"success": False, "message": "Provide kitchen_printed and/or receipt_printed."}, status=400)
        order.save(update_fields=changed)
        return Response({"success": True, "message": "Print status updated.", "order": _order_payload(order)})


class RestaurantLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        return Response({"success": True, "location": {
            "latitude": restaurant.delivery_latitude,
            "longitude": restaurant.delivery_longitude,
            "city": restaurant.city,
            "state": restaurant.state,
            "country": restaurant.country,
            "pincode": restaurant.pincode,
            "address": restaurant.address,
        }})

    def patch(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        allowed = {"latitude": "delivery_latitude", "longitude": "delivery_longitude", "address": "address", "city": "city", "state": "state", "country": "country", "pincode": "pincode"}
        changed = []
        for incoming, field in allowed.items():
            if incoming in request.data:
                setattr(restaurant, field, request.data[incoming])
                changed.append(field)
        if not changed:
            return Response({"success": False, "message": "No supported location fields supplied."}, status=400)
        restaurant.save(update_fields=changed)
        return self.get(request)


class DeliverySummaryAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True, is_deleted=False)
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        if latitude is None or longitude is None:
            return Response({"success": False, "message": "latitude and longitude are required."}, status=400)
        try:
            summary = get_delivery_summary(restaurant, float(latitude), float(longitude))
        except (TypeError, ValueError):
            return Response({"success": False, "message": "Invalid coordinates."}, status=400)
        return Response({"success": True, "delivery": summary, "pickup": {
            "enabled": restaurant.pickup_enabled,
            "cash_on_pickup": restaurant.cash_on_pickup,
        }})


class FulfillmentOptionsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True, is_deleted=False)
        return Response({"success": True, "options": {
            "dinein": True,
            "pickup": restaurant.pickup_enabled,
            "delivery": restaurant.delivery_enabled,
            "cash_on_pickup": restaurant.cash_on_pickup,
            "cash_on_delivery": restaurant.cash_on_delivery,
            "minimum_delivery_order": restaurant.minimum_delivery_order,
            "free_delivery_radius_km": restaurant.free_delivery_radius_km,
            "maximum_delivery_radius_km": restaurant.maximum_delivery_radius_km,
            "delivery_charge_per_km": restaurant.delivery_charge_per_km,
        }})


class DeliveryPartnerListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        partners = DeliveryPartner.objects.filter(restaurant=restaurant).order_by("first_name", "last_name")
        return Response({"success": True, "count": partners.count(), "delivery_partners": [self.serialize(p) for p in partners]})

    @staticmethod
    def serialize(p):
        return {"id": p.id, "first_name": p.first_name, "last_name": p.last_name, "full_name": p.full_name, "phone": p.phone, "email": p.email, "vehicle_type": p.vehicle_type, "vehicle_number": p.vehicle_number, "is_active": p.is_active, "is_available": p.is_available, "is_verified": p.is_verified, "latitude": p.current_latitude, "longitude": p.current_longitude, "last_location_update": p.last_location_update}

    def post(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        required = ["first_name", "phone"]
        missing = [x for x in required if not request.data.get(x)]
        if missing:
            return Response({"success": False, "message": f"Required fields: {', '.join(missing)}."}, status=400)
        try:
            partner = DeliveryPartner.objects.create(restaurant=restaurant, first_name=request.data["first_name"].strip(), last_name=request.data.get("last_name", "").strip(), country_code=request.data.get("country_code", "+91"), phone=request.data["phone"].strip(), alternate_phone=request.data.get("alternate_phone", "").strip(), email=request.data.get("email", "").strip(), address=request.data.get("address", ""), city=request.data.get("city", ""), state=request.data.get("state", ""), pincode=request.data.get("pincode"), vehicle_type=request.data.get("vehicle_type", "bike"), vehicle_number=request.data.get("vehicle_number", ""), driving_license_number=request.data.get("driving_license_number", ""), notes=request.data.get("notes", ""))
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=400)
        return Response({"success": True, "delivery_partner": self.serialize(partner)}, status=201)


class DeliveryPartnerDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_partner(self, request, partner_id):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return None, error
        return get_object_or_404(DeliveryPartner, id=partner_id, restaurant=restaurant), None

    def get(self, request, partner_id):
        partner, error = self.get_partner(request, partner_id)
        if error:
            return error
        return Response({"success": True, "delivery_partner": DeliveryPartnerListCreateAPIView.serialize(partner)})

    def patch(self, request, partner_id):
        partner, error = self.get_partner(request, partner_id)
        if error:
            return error
        editable = ["first_name", "last_name", "country_code", "phone", "alternate_phone", "email", "address", "city", "state", "pincode", "vehicle_type", "vehicle_number", "driving_license_number", "is_active", "is_verified", "notes"]
        changed = []
        for field in editable:
            if field in request.data:
                setattr(partner, field, request.data[field])
                changed.append(field)
        if changed:
            partner.save(update_fields=changed + ["updated_at"])
        return Response({"success": True, "delivery_partner": DeliveryPartnerListCreateAPIView.serialize(partner)})

    def delete(self, request, partner_id):
        partner, error = self.get_partner(request, partner_id)
        if error:
            return error
        if Order.objects.filter(delivery_partner=partner, is_deleted=False, delivery_status__in=["assigned", "picked", "out_for_delivery"]).exists():
            return Response({"success": False, "message": "Partner has active delivery assignments."}, status=400)
        partner.is_active = False
        partner.is_available = False
        partner.resigned_at = timezone.now()
        partner.save(update_fields=["is_active", "is_available", "resigned_at", "updated_at"])
        return Response({"success": True, "message": "Delivery partner deactivated."})


class DeliveryPartnerAvailabilityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, partner_id):
        partner = get_object_or_404(DeliveryPartner, id=partner_id, restaurant=get_restaurant(request))
        if not partner.is_active:
            return Response({"success": False, "message": "Inactive delivery partner cannot be made available."}, status=400)
        partner.is_available = bool(request.data.get("is_available"))
        partner.save(update_fields=["is_available", "updated_at"])
        return Response({"success": True, "is_available": partner.is_available})


class DeliveryPartnerLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, partner_id):
        partner = get_object_or_404(DeliveryPartner, id=partner_id, restaurant=get_restaurant(request))
        try:
            lat = float(request.data.get("latitude")); lng = float(request.data.get("longitude"))
            if not -90 <= lat <= 90 or not -180 <= lng <= 180:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"success": False, "message": "Valid latitude and longitude are required."}, status=400)
        partner.current_latitude = lat; partner.current_longitude = lng; partner.last_location_update = timezone.now()
        partner.save(update_fields=["current_latitude", "current_longitude", "last_location_update", "updated_at"])
        return Response({"success": True, "partner_id": partner.id, "latitude": lat, "longitude": lng, "updated_at": partner.last_location_update})


class AvailableDeliveryPartnersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        partners = DeliveryPartner.objects.filter(restaurant=restaurant, is_active=True, is_available=True)
        return Response({"success": True, "count": partners.count(), "delivery_partners": [DeliveryPartnerListCreateAPIView.serialize(p) for p in partners]})


class AssignDeliveryPartnerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        order = get_object_or_404(Order, id=order_id, restaurant=restaurant, is_deleted=False)
        if order.order_type != "delivery":
            return Response({"success": False, "message": "Delivery partner can only be assigned to delivery orders."}, status=400)
        partner_id = request.data.get("delivery_partner")
        if not partner_id:
            return Response({"success": False, "message": "delivery_partner is required."}, status=400)
        if order.delivery_partner_id:
            return Response({"success": False, "message": "A delivery partner is already assigned. Unassign it first."}, status=400)
        partner = get_object_or_404(DeliveryPartner, id=partner_id, restaurant=restaurant)
        if not partner.is_active or not partner.is_available:
            return Response({"success": False, "message": "Selected delivery partner is inactive or unavailable."}, status=400)
        order.delivery_partner = partner
        order.delivery_status = "assigned"
        order.assigned_at = timezone.now()
        order.save(update_fields=["delivery_partner", "delivery_status", "assigned_at"])
        partner.is_available = False
        partner.save(update_fields=["is_available", "updated_at"])
        return Response({"success": True, "message": "Delivery partner assigned successfully.", "order": _order_payload(order), "partner": DeliveryPartnerListCreateAPIView.serialize(partner)})


class UnassignDeliveryPartnerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        order = get_object_or_404(Order, id=order_id, restaurant=restaurant, is_deleted=False)
        if not order.delivery_partner_id:
            return Response({"success": False, "message": "No delivery partner is assigned."}, status=400)
        if order.delivery_status == "delivered":
            return Response({"success": False, "message": "Delivered orders cannot be unassigned."}, status=400)
        partner = order.delivery_partner
        partner.is_available = True
        partner.save(update_fields=["is_available", "updated_at"])
        order.delivery_partner = None; order.delivery_status = "not_required"; order.assigned_at = None; order.picked_at = None; order.delivered_at = None
        order.save(update_fields=["delivery_partner", "delivery_status", "assigned_at", "picked_at", "delivered_at"])
        return Response({"success": True, "message": "Delivery partner unassigned successfully.", "order": _order_payload(order)})


class DeliveryStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        restaurant, error = _restaurant_or_404(request)
        if error:
            return error
        order = get_object_or_404(Order, id=order_id, restaurant=restaurant, is_deleted=False)
        if order.order_type != "delivery":
            return Response({"success": False, "message": "Only delivery orders have delivery status."}, status=400)
        new_status = request.data.get("delivery_status")
        try:
            order = update_delivery_status(order, new_status)
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=400)
        return Response({"success": True, "order": _order_payload(order)})


class DeliveryTrackingPublicAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, is_deleted=False)
        if order.order_type != "delivery":
            return Response({"success": False, "message": "Tracking is available only for delivery orders."}, status=400)
        partner = order.delivery_partner
        return Response({"success": True, "tracking": {
            "order_id": order.id,
            "order_number": order.order_number,
            "delivery_status": order.delivery_status,
            "partner": ({"id": partner.id, "name": partner.full_name, "phone": partner.phone, "latitude": partner.current_latitude, "longitude": partner.current_longitude, "last_location_update": partner.last_location_update} if partner else None),
            "delivery_latitude": order.delivery_latitude,
            "delivery_longitude": order.delivery_longitude,
            "assigned_at": order.assigned_at,
            "picked_at": order.picked_at,
            "delivered_at": order.delivered_at,
        }})


class InventoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_restaurant(self, request):
        return get_restaurant(request)

    def get(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        qs = InventoryItem.objects.filter(restaurant=restaurant, is_active=True).select_related("food_item")
        data = [{"id": x.id, "name": x.name, "sku": x.sku, "unit": x.unit, "quantity": x.quantity, "reorder_level": x.reorder_level, "cost_price": x.cost_price, "food_item": x.food_item_id, "low_stock": x.quantity <= x.reorder_level, "notes": x.notes} for x in qs]
        return Response({"success": True, "count": len(data), "inventory": data})

    def post(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        food_item = None
        if request.data.get("food_item"):
            food_item = get_object_or_404(FoodItem, id=request.data["food_item"], restaurant=restaurant)
        item = InventoryItem.objects.create(restaurant=restaurant, food_item=food_item, name=request.data.get("name", food_item.name if food_item else "").strip(), sku=request.data.get("sku", ""), unit=request.data.get("unit", "unit"), quantity=request.data.get("quantity", 0), reorder_level=request.data.get("reorder_level", 0), cost_price=request.data.get("cost_price", 0), notes=request.data.get("notes", ""))
        return Response({"success": True, "inventory_id": item.id}, status=201)


class InventoryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, inventory_id):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        item = get_object_or_404(InventoryItem, id=inventory_id, restaurant=restaurant)
        fields = ["name", "sku", "unit", "quantity", "reorder_level", "cost_price", "is_active", "notes"]
        changed = []
        for field in fields:
            if field in request.data:
                setattr(item, field, request.data[field]); changed.append(field)
        if changed: item.save(update_fields=changed + ["updated_at"])
        return Response({"success": True, "inventory_id": item.id, "quantity": item.quantity, "low_stock": item.quantity <= item.reorder_level})

    def delete(self, request, inventory_id):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        item = get_object_or_404(InventoryItem, id=inventory_id, restaurant=restaurant)
        item.is_active = False; item.save(update_fields=["is_active", "updated_at"])
        return Response({"success": True, "message": "Inventory item archived."})


class CouponListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        qs = Coupon.objects.filter(restaurant=restaurant)
        return Response({"success": True, "count": qs.count(), "coupons": [self.serialize(c) for c in qs]})

    @staticmethod
    def serialize(c):
        return {"id": c.id, "code": c.code, "discount_type": c.discount_type, "value": c.value, "minimum_order_amount": c.minimum_order_amount, "maximum_discount": c.maximum_discount, "usage_limit": c.usage_limit, "used_count": c.used_count, "valid_from": c.valid_from, "valid_until": c.valid_until, "applies_to_dinein": c.applies_to_dinein, "applies_to_pickup": c.applies_to_pickup, "applies_to_delivery": c.applies_to_delivery, "is_active": c.is_active}

    def post(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        code = str(request.data.get("code", "")).strip().upper()
        if not code: return Response({"success": False, "message": "code is required."}, status=400)
        try:
            coupon = Coupon.objects.create(restaurant=restaurant, code=code, discount_type=request.data.get("discount_type", "percent"), value=request.data.get("value", 0), minimum_order_amount=request.data.get("minimum_order_amount", 0), maximum_discount=request.data.get("maximum_discount"), usage_limit=request.data.get("usage_limit"), valid_from=request.data.get("valid_from"), valid_until=request.data.get("valid_until"), applies_to_dinein=request.data.get("applies_to_dinein", True), applies_to_pickup=request.data.get("applies_to_pickup", True), applies_to_delivery=request.data.get("applies_to_delivery", True))
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=400)
        return Response({"success": True, "coupon": self.serialize(coupon)}, status=201)


class CouponDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, coupon_id):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        coupon = get_object_or_404(Coupon, id=coupon_id, restaurant=restaurant)
        fields = ["code", "discount_type", "value", "minimum_order_amount", "maximum_discount", "usage_limit", "valid_from", "valid_until", "applies_to_dinein", "applies_to_pickup", "applies_to_delivery", "is_active"]
        for field in fields:
            if field in request.data: setattr(coupon, field, request.data[field])
        coupon.save()
        return Response({"success": True, "coupon": CouponListCreateAPIView.serialize(coupon)})

    def delete(self, request, coupon_id):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        coupon = get_object_or_404(Coupon, id=coupon_id, restaurant=restaurant)
        coupon.is_active = False; coupon.save(update_fields=["is_active", "updated_at"])
        return Response({"success": True, "message": "Coupon deactivated."})


class CouponValidateAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True, is_deleted=False)
        code = str(request.data.get("code", "")).strip().upper()
        order_amount = Decimal(str(request.data.get("order_amount", "0")))
        order_type = request.data.get("order_type", "dinein")
        coupon = Coupon.objects.filter(restaurant=restaurant, code=code, is_active=True).first()
        if not coupon: return Response({"success": False, "message": "Invalid or inactive coupon."}, status=400)
        now = timezone.now()
        if coupon.valid_from and now < coupon.valid_from: return Response({"success": False, "message": "Coupon is not active yet."}, status=400)
        if coupon.valid_until and now > coupon.valid_until: return Response({"success": False, "message": "Coupon has expired."}, status=400)
        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit: return Response({"success": False, "message": "Coupon usage limit reached."}, status=400)
        if order_amount < coupon.minimum_order_amount: return Response({"success": False, "message": "Minimum order amount not reached."}, status=400)
        if not getattr(coupon, f"applies_to_{order_type}", False): return Response({"success": False, "message": "Coupon does not apply to this order type."}, status=400)
        discount = order_amount * coupon.value / Decimal("100") if coupon.discount_type == "percent" else coupon.value
        if coupon.maximum_discount is not None: discount = min(discount, coupon.maximum_discount)
        discount = min(discount, order_amount).quantize(Decimal("0.01"))
        return Response({"success": True, "coupon": {"id": coupon.id, "code": coupon.code}, "discount_amount": discount})


class ReviewListCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True, is_deleted=False)
        qs = Review.objects.filter(restaurant=restaurant, is_published=True)
        return Response({"success": True, "count": qs.count(), "average_rating": qs.aggregate(avg=Avg("rating"))["avg"] or 0, "reviews": [self.serialize(x) for x in qs]})

    @staticmethod
    def serialize(x):
        return {"id": x.id, "customer_name": x.customer_name, "rating": x.rating, "comment": x.comment, "owner_response": x.owner_response, "created_at": x.created_at}

    def post(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True, is_deleted=False)
        rating = int(request.data.get("rating", 0))
        if rating < 1 or rating > 5:
            return Response({"success": False, "message": "rating must be between 1 and 5."}, status=400)
        order = None
        if request.data.get("order_id"):
            order = get_object_or_404(Order, id=request.data["order_id"], restaurant=restaurant, is_deleted=False)
        review = Review.objects.create(restaurant=restaurant, order=order, customer_name=str(request.data.get("customer_name", "Customer"))[:120], customer_email=request.data.get("customer_email", ""), rating=rating, comment=request.data.get("comment", ""))
        return Response({"success": True, "review": self.serialize(review)}, status=201)


class ReviewDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, review_id):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        review = get_object_or_404(Review, id=review_id, restaurant=restaurant)
        for field in ["owner_response", "is_published"]:
            if field in request.data: setattr(review, field, request.data[field])
        review.save()
        return Response({"success": True, "review": ReviewListCreateAPIView.serialize(review)})


class ReportsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = _restaurant_or_404(request)
        if error: return error
        report = {
            "restaurant": get_restaurant_statistics(restaurant=restaurant),
            "sales": get_sales_statistics(restaurant=restaurant),
            "period_sales": {"today": get_daily_sales(restaurant=restaurant), "last_7_days": get_weekly_sales(restaurant=restaurant), "month": get_monthly_sales(restaurant=restaurant), "year": get_yearly_sales(restaurant=restaurant)},
            "orders": get_order_statistics(restaurant=restaurant),
            "menu": get_menu_statistics(restaurant=restaurant),
            "staff": get_staff_statistics(restaurant=restaurant),
            "delivery": get_delivery_statistics(restaurant=restaurant),
            "customers": get_customer_statistics(restaurant=restaurant),
            "top_items": list(get_top_selling_items(restaurant=restaurant)),
        }
        return Response({"success": True, "report": report})
