from rest_framework import serializers
from .models import Restaurant

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
        read_only_fields = ['owner']  # ✅ keep owner read-only ONLY

    def update(self, instance, validated_data):
        request = self.context.get('request')

            # 🔥 DEBUG HERE
        print("FILES:", request.FILES)

        # 🔥 HANDLE FILES PROPERLY
        if request and request.FILES:

            if 'logo' in request.FILES:
                # delete old file (optional but recommended)
                if instance.logo:
                    instance.logo.delete(save=False)
                instance.logo = request.FILES['logo']

            if 'cover_image' in request.FILES:
                if instance.cover_image:
                    instance.cover_image.delete(save=False)
                instance.cover_image = request.FILES['cover_image']

        # 🔥 UPDATE NORMAL FIELDS
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
