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
        read_only_fields = ['owner']  # keep owner read-only

    def update(self, instance, validated_data):
        request = self.context.get('request', None)

        # ✅ SAFE DEBUG (won’t crash)
        if request:
            print("FILES:", request.FILES)

        # 🔥 HANDLE FILE UPLOADS SAFELY
        if request and request.FILES:

            # ✅ LOGO
            if 'logo' in request.FILES:
                new_logo = request.FILES.get('logo')

                if new_logo:
                    if instance.logo:
                        instance.logo.delete(save=False)  # remove old file
                    instance.logo = new_logo

            # ✅ COVER IMAGE
            if 'cover_image' in request.FILES:
                new_cover = request.FILES.get('cover_image')

                if new_cover:
                    if instance.cover_image:
                        instance.cover_image.delete(save=False)
                    instance.cover_image = new_cover

        # 🔥 UPDATE NORMAL FIELDS
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
