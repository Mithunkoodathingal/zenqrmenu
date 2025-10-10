# restaurant/apps.py
from django.apps import AppConfig

class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'

    def ready(self):
        # import signal handlers so they are registered when app is ready
        # do NOT put heavy logic here — only imports
        import restaurant.signals  # noqa: F401
