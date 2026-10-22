import os
import logging
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List, Optional

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("casa")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

SEED_DATE = "2026-09-01T00:00:00+00:00"
LEVEL_ORDER = ["L0", "L1", "L2", "L3", "L4"]
VERSION_STATUSES = ["draft", "review", "published", "retired"]

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


LEVEL_FLAG = "CASA_LEVEL_FROM_ASSESSMENT_MODULE_VERSION"
GRANTS_FLAG = "CASA_EXTRA_ATTEMPT_GRANTS"


def flag(name: str) -> bool:
    """Behaviour switches: off unless the environment sets them to 1 (off on the shared preproduction instance)."""
    return os.environ.get(name) == "1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseDocument(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: PyObjectId = Field(alias="_id")

    @classmethod
    def from_mongo(cls, doc: Optional[dict]):
        return cls(**doc) if doc else None

    def to_mongo(self) -> dict:
        data = self.model_dump()
        data["_id"] = data.pop("id")
        return data

    def out(self) -> dict:
        return self.model_dump()


class VersionedEntity(BaseDocument):
    code: str
    published_version: int
    latest_version: int
    created_at: str
    updated_at: str


class EntityVersion(BaseDocument):
    entity_id: str
    version: int
    status: str
    changelog: str
    created_at: str
    published_at: Optional[str] = None


async def insert_missing(collection, doc: BaseDocument):
    data = doc.to_mongo()
    _id = data.pop("_id")
    await db[collection].update_one({"_id": _id}, {"$setOnInsert": data}, upsert=True)


async def log_change(user, entity_type: str, entity_id: str, action: str, details: str = "", version: Optional[int] = None):
    await db.catalog_change_log.insert_one({"at": now_iso(), "user_id": user.id, "user_email": user.email, "user_name": f"{user.first_name} {user.last_name}",
                                            "entity_type": entity_type, "entity_id": entity_id, "version": version, "action": action, "details": details})


async def versions_by_key(version_coll: str) -> dict:
    out = {}
    async for d in db[version_coll].find({"status": {"$in": ["published", "retired"]}}):
        v = EntityVersion.from_mongo(d).out()
        v["id"] = v.pop("entity_id")
        out[f"{v['id']}@{v['version']}"] = v
    return out


def pinned(items: dict, key: str, version) -> Optional[dict]:
    return items.get(f"{key}@{version}") if version else None


async def upsert(collection, doc: BaseDocument):
    data = doc.to_mongo()
    await db[collection].replace_one({"_id": data["_id"]}, data, upsert=True)


def norm(text: str) -> str:
    return unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()


async def all_docs(coll: str, sort_field: str = "order") -> List[dict]:
    docs = await db[coll].find().sort(sort_field, 1).to_list(1000)
    return [BaseDocument.from_mongo(d).out() for d in docs]


async def published(entity_coll: str, version_coll: str) -> List[dict]:
    entities = await db[entity_coll].find().sort("_id", 1).to_list(1000)
    out = []
    for e in entities:
        ent = VersionedEntity.from_mongo(e)
        ver = await db[version_coll].find_one({"entity_id": ent.id, "version": ent.published_version, "status": "published"})
        if ver:
            v = EntityVersion.from_mongo(ver).out()
            v.pop("entity_id")
            v["id"] = ent.id
            out.append(v)
    return out
