from rest_framework import serializers
from .models import Restaurant, Order, OrderItem, FoodItem, AddOn, Category


# ================= RESTAURANT =================


class RestaurantSerializer(serializers.ModelSerializer):

    logo_url = serializers.SerializerMethodField()

    cover_image_url = serializers.SerializerMethodField()

    class Meta:

        model = Restaurant

        fields = [
            'id',
            'owner',
            'name',
            'address',
            'about',
            'cover_image',
            'cover_image_url',
            'logo',
            'logo_url',
            'phone',
            'cuisine_type',
        ]

        read_only_fields = ['owner']

    # =====================================================
    # LOGO URL
    # =====================================================

    def get_logo_url(self, obj):

        request = self.context.get('request')

        if not obj.logo:
            return None

        try:

            if request:
                return request.build_absolute_uri(
                    obj.logo.url
                )

            return obj.logo.url

        except Exception as e:

            print("LOGO URL ERROR:", str(e))

            return None

    # =====================================================
    # COVER IMAGE URL
    # =====================================================

    def get_cover_image_url(self, obj):

        request = self.context.get('request')

        if not obj.cover_image:
            return None

        try:

            if request:
                return request.build_absolute_uri(
                    obj.cover_image.url
                )

            return obj.cover_image.url

        except Exception as e:

            print("COVER URL ERROR:", str(e))

            return None

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, instance, validated_data):

        request = self.context.get('request', None)

        if request:
            print("FILES:", request.FILES)

        # =====================================================
        # REMOVE FILE FIELDS FROM VALIDATED DATA
        # IMPORTANT FIX
        # =====================================================

        validated_data.pop('logo', None)

        validated_data.pop('cover_image', None)

        # =====================================================
        # HANDLE LOGO
        # =====================================================

        if request and request.FILES.get('logo'):

            new_logo = request.FILES.get('logo')

            if new_logo:

                # avoid deleting default image
                if (
                    instance.logo and
                    'default/' not in str(instance.logo)
                ):

                    try:
                        instance.logo.delete(save=False)
                    except Exception as e:
                        print(str(e))

                instance.logo = new_logo

        # =====================================================
        # HANDLE COVER IMAGE
        # =====================================================

        if request and request.FILES.get('cover_image'):

            new_cover = request.FILES.get(
                'cover_image'
            )

            if new_cover:

                if (
                    instance.cover_image and
                    'default/' not in str(instance.cover_image)
                ):

                    try:
                        instance.cover_image.delete(
                            save=False
                        )
                    except Exception as e:
                        print(str(e))

                instance.cover_image = new_cover

        # =====================================================
        # NORMAL TEXT FIELDS
        # =====================================================

        for attr, value in validated_data.items():

            setattr(instance, attr, value)

        instance.save()

        instance.refresh_from_db()

        return instance


# ================= FOOD ITEM ================= #


class FoodItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = '__all__'   # OR explicitly add 'is_veg'


# ================= ORDER ITEM =================

class OrderItemSerializer(serializers.ModelSerializer):
    food_item_id = serializers.IntegerField(write_only=True)
    selected_addons_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    food_item_name = serializers.CharField(source='food_item.name', read_only=True)

    is_veg = serializers.BooleanField(source='food_item.is_veg', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'food_item_id',
            'food_item_name',
            'quantity',
            'is_veg',
            'selected_addons_ids',
            'selected_addons'
        ]
        read_only_fields = ['selected_addons']

# =================== CATEGORY SERIALIZER ============== #

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]

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