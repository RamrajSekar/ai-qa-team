from abc import ABC, abstractmethod


class SecretStore(ABC):
    @abstractmethod
    async def put(self, project_id: str, value: str) -> str: ...

    @abstractmethod
    async def get(self, project_id: str, credential_ref: str) -> str: ...

    @abstractmethod
    async def replace(self, project_id: str, credential_ref: str, value: str) -> str: ...

    @abstractmethod
    async def delete(self, project_id: str, credential_ref: str) -> None: ...
