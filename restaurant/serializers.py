from rest_framework import serializers
from .models import Restaurant, Order, OrderItem, FoodItem, AddOn


# ================= RESTAURANT =================

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            'id',
            'owner',
            'name',
            'address',
            'about',
            'cover_image',
            'logo',
            'phone',
            'cuisine_type',
        ]
        read_only_fields = ['owner']

    def update(self, instance, validated_data):
        request = self.context.get('request', None)

        # DEBUG
        if request:
            print("FILES:", request.FILES)

        # HANDLE FILES
        if request and request.FILES:

            if 'logo' in request.FILES:
                new_logo = request.FILES.get('logo')
                if new_logo:
                    if instance.logo:
                        instance.logo.delete(save=False)
                    instance.logo = new_logo

            if 'cover_image' in request.FILES:
                new_cover = request.FILES.get('cover_image')
                if new_cover:
                    if instance.cover_image:
                        instance.cover_image.delete(save=False)
                    instance.cover_image = new_cover

        # NORMAL FIELDS
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


# ================= ORDER ITEM =================

class OrderItemSerializer(serializers.ModelSerializer):
    food_item_id = serializers.IntegerField(write_only=True)
    selected_addons_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    food_item_name = serializers.CharField(source='food_item.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'food_item_id',
            'food_item_name',
            'quantity',
            'selected_addons_ids',
            'selected_addons'
        ]
        read_only_fields = ['selected_addons']


# ================= ORDER =================

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'restaurant',
            'table',
            'customer_name',
            'customer_phone',
            'status',  # ✅ NOW WRITABLE
            'is_completed',
            'created_at',
            'total_price_cached',
            'items',
            'order_items'
        ]
        # ❌ REMOVED status from read_only
        read_only_fields = ['is_completed', 'created_at', 'total_price_cached']

    # ================= CREATE =================
    def create(self, validated_data):
        items_data = validated_data.pop('items')

        table = validated_data.get('table')
        restaurant = table.restaurant

        order = Order.objects.create(
            table=table,
            restaurant=restaurant,
            customer_name=validated_data.get('customer_name', ''),
            customer_phone=validated_data.get('customer_phone', '')
        )

        total = 0

        for item in items_data:
            food_item = FoodItem.objects.get(id=item['food_item_id'])
            quantity = item.get('quantity', 1)

            # 🔒 SECURITY CHECK
            if food_item.restaurant != restaurant:
                raise serializers.ValidationError("Invalid food item for this restaurant")

            order_item = OrderItem.objects.create(
                order=order,
                food_item=food_item,
                quantity=quantity
            )

            addon_ids = item.get('selected_addons_ids', [])
            if addon_ids:
                addons = AddOn.objects.filter(id__in=addon_ids)
                order_item.selected_addons.set(addons)

            base = (food_item.price or 0) * quantity
            addons_price = sum(a.price for a in order_item.selected_addons.all()) * quantity
            total += base + addons_price

        order.total_price_cached = total
        order.save()

        return order

    # ================= UPDATE (FIX FOR PATCH) =================
    def update(self, instance, validated_data):
        status = validated_data.get('status', instance.status)

        instance.status = status

        # ✅ SYNC BOOLEAN FIELD
        if status == 'completed':
            instance.is_completed = True
        else:
            instance.is_completed = False

        instance.save()
        return instance