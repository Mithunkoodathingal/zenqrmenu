from django.apps import AppConfig

# restaurant/apps.py


class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'

    def ready(self):
        # import signal handlers
        import restaurant.signals  # noqa



class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'
