# restaurant/apps.py
from django.apps import AppConfig

class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'

    def ready(self):
        # Import signal handlers so they are registered when app is ready.
        import restaurant.signals  # noqa: F401
        # Register supplemental API domain models without changing the existing
        # restaurant/models.py module.
        import restaurant.feature_models  # noqa: F401
