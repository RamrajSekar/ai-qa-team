"""Storage-admission double for design-contract tests, NOT quota/concurrency proof.

Real transaction/counter invariants are exercised by verify_resource_quota.py and
verify_test_design_qualification.py on a separate loopback Mongo replica set.
"""
from contextlib import asynccontextmanager
from copy import deepcopy
from uuid import uuid4


class ResourceQuotaDouble:
    def __init__(self, database): self.db = database
    @asynccontextmanager
    async def admission(self, user, project, kind, count, tier="basic", **kwargs):
        yield {"capacity": count, "kind": kind}
    async def persist(self, reservation, document, index):
        doc = deepcopy(document)
        doc.setdefault("_id", uuid4().hex)
        await self.db[reservation["kind"]].insert_one(doc)
        return doc
