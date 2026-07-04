from rest_framework import serializers

from .models import (
    RestaurantGatewaySettings,
    PaymentTransaction,
    PaymentRefund,
    PaymentWebhookLog,
    PaymentAuditLog,
    Receipt,
)


# ==========================================================
# Receipt
# ==========================================================

class ReceiptSerializer(serializers.ModelSerializer):

    class Meta:
        model = Receipt

        fields = (
            "id",
            "receipt_number",
            "pdf",
            "printed",
            "printed_at",
            "email_sent",
            "email_sent_at",
            "whatsapp_sent",
            "whatsapp_sent_at",
            "created_at",
        )

        read_only_fields = fields


# ==========================================================
# Refund
# ==========================================================

class PaymentRefundSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentRefund

        fields = (
            "id",
            "refund_id",
            "amount",
            "reason",
            "status",
            "gateway_response",
            "created_at",
        )

        read_only_fields = (
            "refund_id",
            "status",
            "gateway_response",
            "created_at",
        )


# ==========================================================
# Gateway Settings
# ==========================================================

class RestaurantGatewaySettingsSerializer(serializers.ModelSerializer):

    razorpay_key_id = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    razorpay_key_secret = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    webhook_secret = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    key_id_masked = serializers.SerializerMethodField()

    has_key_secret = serializers.SerializerMethodField()

    has_webhook_secret = serializers.SerializerMethodField()

    class Meta:

        model = RestaurantGatewaySettings

        fields = (

            "id",

            "gateway",

            "environment",

            "currency",

            "merchant_name",

            "merchant_email",

            "verified",

            "verified_at",

            "accept_online",

            "accept_cash_delivery",

            "accept_cash_pickup",

            "is_active",

            "key_id_masked",

            "has_key_secret",

            "has_webhook_secret",

            "razorpay_key_id",

            "razorpay_key_secret",

            "webhook_secret",

            "created_at",

            "updated_at",

        )

        read_only_fields = (

            "verified",

            "verified_at",

            "merchant_name",

            "merchant_email",

            "created_at",

            "updated_at",

        )

    def get_key_id_masked(self, obj):

        value = obj.razorpay_key_id

        if not value:
            return ""

        return "********" + value[-4:]

    def get_has_key_secret(self, obj):

        return bool(obj.razorpay_secret)

    def get_has_webhook_secret(self, obj):

        return bool(obj.webhook_secret_value)

    def validate(self, attrs):

        online = attrs.get(
            "accept_online",
            getattr(self.instance, "accept_online", False)
        )

        key_id = attrs.get("razorpay_key_id")

        secret = attrs.get("razorpay_key_secret")

        if online:

            existing_key = ""

            existing_secret = ""

            if self.instance:

                existing_key = self.instance.razorpay_key_id

                existing_secret = self.instance.razorpay_secret

            if not (key_id or existing_key):

                raise serializers.ValidationError(
                    "Razorpay Key ID is required."
                )

            if not (secret or existing_secret):

                raise serializers.ValidationError(
                    "Razorpay Key Secret is required."
                )

        return attrs

    def create(self, validated_data):

        key_id = validated_data.pop(
            "razorpay_key_id",
            ""
        )

        secret = validated_data.pop(
            "razorpay_key_secret",
            ""
        )

        webhook = validated_data.pop(
            "webhook_secret",
            ""
        )

        obj = RestaurantGatewaySettings.objects.create(
            **validated_data
        )

        if key_id:
            obj.razorpay_key_id = key_id

        if secret:
            obj.razorpay_secret = secret

        if webhook:
            obj.webhook_secret_value = webhook

        obj.save()

        return obj

    def update(self, instance, validated_data):

        key_id = validated_data.pop(
            "razorpay_key_id",
            None
        )

        secret = validated_data.pop(
            "razorpay_key_secret",
            None
        )

        webhook = validated_data.pop(
            "webhook_secret",
            None
        )

        for attr, value in validated_data.items():

            setattr(instance, attr, value)

        if key_id is not None:
            instance.razorpay_key_id = key_id

        if secret:
            instance.razorpay_secret = secret

        if webhook:
            instance.webhook_secret_value = webhook

        instance.save()

        return instance


# ==========================================================
# Payment Transaction
# ==========================================================

class PaymentTransactionSerializer(serializers.ModelSerializer):

    receipt = ReceiptSerializer(
        read_only=True
    )

    refunds = PaymentRefundSerializer(
        many=True,
        read_only=True
    )

    class Meta:

        model = PaymentTransaction

        fields = (

            "id",

            "transaction_number",

            "restaurant",

            "order",

            "gateway",

            "payment_mode",

            "source",

            "status",

            "amount",

            "currency",

            "customer_name",

            "customer_phone",

            "customer_email",

            "gateway_order_id",

            "gateway_payment_id",

            "receipt_number",

            "otp",

            "otp_verified",

            "otp_verified_at",

            "delivery_person_name",

            "delivery_person_phone",

            "delivery_started_at",

            "delivered_at",

            "failure_reason",

            "gateway_response",

            "paid_at",

            "receipt",

            "refunds",

            "created_at",

            "updated_at",

        )

        read_only_fields = (

            "gateway_order_id",

            "gateway_payment_id",

            "gateway_signature",

            "gateway_response",

            "status",

            "paid_at",

            "otp_verified",

            "otp_verified_at",

            "created_at",

            "updated_at",

            "receipt",

            "refunds",

        )


# ==========================================================
# Webhook Log
# ==========================================================

class PaymentWebhookLogSerializer(serializers.ModelSerializer):

    class Meta:

        model = PaymentWebhookLog

        fields = "__all__"

        read_only_fields = "__all__"


# ==========================================================
# Audit Log
# ==========================================================

class PaymentAuditLogSerializer(serializers.ModelSerializer):

    class Meta:

        model = PaymentAuditLog

        fields = "__all__"

        read_only_fields = "__all__"


