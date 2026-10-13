# Define conf

from typing import ClassVar
from pydantic import BaseModel, ConfigDict
from .hashing import sha

# Define class Cfg
class Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # Speed
    HASH_EXCLUDE: ClassVar[frozenset[str]] = frozenset()

    # Fingerprint
    def fingerprint(self) -> str:
        return sha(self.model_dump(mode="json", exclude=set(self.HASH_EXCLUDE)))