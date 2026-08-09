from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("restaurant", "0025_auditlog_kitchennote_staff_staffattendance_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("sku", models.CharField(blank=True, max_length=80)),
                ("unit", models.CharField(default="unit", max_length=30)),
                ("quantity", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=12)),
                ("reorder_level", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=12)),
                ("cost_price", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("food_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="inventory_records", to="restaurant.fooditem")),
                ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_items", to="restaurant.restaurant")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Coupon",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50)),
                ("discount_type", models.CharField(choices=[("percent", "Percentage"), ("fixed", "Fixed")], default="percent", max_length=10)),
                ("value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("minimum_order_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("maximum_discount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("usage_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("used_count", models.PositiveIntegerField(default=0)),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("applies_to_dinein", models.BooleanField(default=True)),
                ("applies_to_pickup", models.BooleanField(default=True)),
                ("applies_to_delivery", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coupons", to="restaurant.restaurant")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_name", models.CharField(max_length=120)),
                ("customer_email", models.EmailField(blank=True, max_length=254)),
                ("rating", models.PositiveSmallIntegerField()),
                ("comment", models.TextField(blank=True)),
                ("owner_response", models.TextField(blank=True)),
                ("is_published", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviews", to="restaurant.order")),
                ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="restaurant.restaurant")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CouponRedemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("discount_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("coupon", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="redemptions", to="restaurant.coupon")),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="coupon_redemption", to="restaurant.order")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.UniqueConstraint(fields=("restaurant", "name"), name="unique_inventory_item_per_restaurant"),
        ),
        migrations.AddConstraint(
            model_name="coupon",
            constraint=models.UniqueConstraint(fields=("restaurant", "code"), name="unique_coupon_code_per_restaurant"),
        ),
        migrations.AddIndex(model_name="inventoryitem", index=models.Index(fields=["restaurant", "is_active"], name="restaurant_i_restaur_0d7c2f_idx")),
        migrations.AddIndex(model_name="inventoryitem", index=models.Index(fields=["restaurant", "sku"], name="restaurant_i_restaur_0b2a55_idx")),
        migrations.AddIndex(model_name="coupon", index=models.Index(fields=["restaurant", "code"], name="restaurant_c_coupon_8fdb0f_idx")),
        migrations.AddIndex(model_name="coupon", index=models.Index(fields=["restaurant", "is_active"], name="restaurant_c_coupon_2bce93_idx")),
        migrations.AddIndex(model_name="review", index=models.Index(fields=["restaurant", "is_published"], name="restaurant_r_restaur_57a7a4_idx")),
        migrations.AddIndex(model_name="review", index=models.Index(fields=["restaurant", "rating"], name="restaurant_r_restaur_4b6b1d_idx")),
    ]
