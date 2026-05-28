from rest_framework import serializers
from .models import SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "price",
            "duration_days",
            "table_limit",
            "menu_item_limit",
            "features",
        ]

    def get_features(self, obj):
        if not obj.features:
            return []

        return [
            feature.strip()
            for feature in obj.features.split("\n")
            if feature.strip()
        ]