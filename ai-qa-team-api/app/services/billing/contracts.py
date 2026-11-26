from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaidInvoice:
    provider: str
    invoice_id: str
    customer_id: str
    subscription_id: str
    price_id: str
    amount_paid: int
    subtotal: int
    currency: str
    paid_until: int
    livemode: bool
    current: bool
    reason: str


@dataclass(frozen=True)
class BillingEvent:
    event_id: str
    action: str
    object_id: str
    reason: str = ""


class BillingProvider(Protocol):
    name: str
    hosted_domains: dict[str, str]
    async def create_customer(self, account_id: str, operation_id: str) -> str: ...
    async def price(self, price_id: str) -> dict: ...
    async def checkout(self, operation: dict, customer_id: str) -> dict: ...
    async def portal(self, customer_id: str) -> str: ...
    def verify_event(self, payload: bytes, signature: str) -> dict: ...
    async def paid_invoice(self, invoice_id: str) -> PaidInvoice: ...
    async def subscription(self, subscription_id: str) -> dict: ...
    async def normalize_event(self, event: dict) -> list[BillingEvent]: ...
