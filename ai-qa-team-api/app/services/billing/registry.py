from fastapi import HTTPException
from contextlib import asynccontextmanager
from app.services.billing.stripe_provider import StripeProvider


class BillingProviderRegistry:
    def __init__(self):
        self.factories = {"stripe": StripeProvider}

    def resolve(self, provider):
        factory = self.factories.get(provider)
        if not factory:
            raise HTTPException(503, "This subscription's billing provider is unavailable.")
        return factory()

    @asynccontextmanager
    async def active(self, provider):
        adapter = self.resolve(provider)
        try:
            yield adapter
        finally:
            close = getattr(adapter, "aclose", None)
            if close is not None:
                await close()


billing_providers = BillingProviderRegistry()
