from rest_framework import serializers
from .models import Restaurant


class RestaurantSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id',
            'name',
            'address',
            'about',
            'logo',
            'cover_image'
        ]

    def get_logo(self, obj):
        if obj.logo:
            return obj.logo.url
        return None

    def get_cover_image(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None