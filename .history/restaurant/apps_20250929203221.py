from django.apps import AppConfig
# restaurant/apps.py
# restaurant/apps.py
from django.apps import AppConfig

class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'

    def ready(self):
        # register signals
        import restaurant.signals  # noqa


class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'

    def ready(self):
        # import signal handlers
        import restaurant.signals  # noqa



class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'
