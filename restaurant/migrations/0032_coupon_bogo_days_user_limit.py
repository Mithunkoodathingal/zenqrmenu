from django.db import migrations, models


class Migration(migrations.Migration):
    """Additive only: new nullable/defaulted coupon fields + 'bogo' choice."""

    dependencies = [
        ("restaurant", "0031_alter_appnotification_options_alter_branch_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="coupon",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coupon",
            name="per_user_limit",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="coupon",
            name="applicable_days",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="coupon",
            name="discount_type",
            field=models.CharField(
                choices=[("percent", "Percentage"), ("fixed", "Fixed"), ("bogo", "Buy one get one")],
                default="percent",
                max_length=10,
            ),
        ),
    ]
