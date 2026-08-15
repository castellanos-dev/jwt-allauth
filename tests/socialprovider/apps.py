from django.apps import AppConfig


class DummyProviderConfig(AppConfig):
    name = 'tests.socialprovider'
    label = 'tests_socialprovider'
    verbose_name = 'Dummy social provider'
