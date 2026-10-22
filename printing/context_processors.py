"""
printing/context_processors.py
==============================
Context processor to inject current kiosk shop information and rates
globally into all template contexts.
"""

from .models import Shop


def kiosk_context(request):
    """
    Supplies the default shop and its pricing to all templates.
    """
    shop_slug = request.GET.get('shop') or request.session.get('kiosk_shop_slug')
    shop = None
    if shop_slug:
        shop = Shop.objects.filter(slug=shop_slug, is_active=True).first()

    if not shop:
        shop = Shop.get_default_shop()

    # Store shop slug in session for subsequent customer pages
    request.session['kiosk_shop_slug'] = shop.slug

    return {
        'current_shop': shop,
        'current_pricing': getattr(shop, 'pricing', None),
    }
