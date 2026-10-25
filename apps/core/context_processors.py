from django.conf import settings


def currency(request):
    return {"CURRENCY_CODE": settings.CURRENCY_CODE}
