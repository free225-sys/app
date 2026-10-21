"""Remove content and accounts created by automated test runs after a given ISO timestamp (journal kept)."""
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
if len(sys.argv) < 3 or sys.argv[2] != "--whitelist":
    raise SystemExit("Usage : cleanup_test_runs.py <horodatage ISO> --whitelist <fichier> (liste blanche explicite obligatoire en préproduction)")
since = sys.argv[1]
WHITE = {line.strip() for line in open(sys.argv[3]) if line.strip()}
rx = {"$regex": "^(test-|QA-|qa-)"}
PROTECTED = ["M-001", "CO-001", "CO-002", "P-001", "P-002", "A-M-001-G"] + [f"Q-M-001-G{i}" for i in range(1, 6)]
for ent, ver in (("concepts", "concept_versions"), ("modules", "module_versions"), ("resources", "resource_versions")):
    ids = sorted((set(db[ver].distinct("entity_id", {"entity_id": rx})) | set(db[ent].distinct("_id", {"_id": rx}))) & WHITE)
    db[ver].delete_many({"entity_id": {"$in": ids}})
    db[ent].delete_many({"_id": {"$in": ids}})
    print(ent, "removed:", ids)
for coll in ("concept_versions", "module_versions"):
    drafts = list(db[coll].find({"status": {"$in": ["draft", "review"]}, "created_at": {"$gte": since}, "changelog": {"$not": {"$regex": "CERT-DOC-01"}},
                                 "entity_id": {"$nin": PROTECTED}}, {"entity_id": 1, "version": 1}))
    drafts = [d for d in drafts if f"{d['entity_id']}@{d['version']}" in WHITE]
    for d in drafts:
        db[coll].delete_one({"_id": d["_id"]})
        db[coll.replace("_versions", "s")].update_one({"_id": d["entity_id"]}, {"$set": {"latest_version": d["version"] - 1}})
    print(coll, "test drafts removed:", [(d["entity_id"], d["version"]) for d in drafts])
users = list(db.users.find({"created_at": {"$gte": since}, "email": {"$in": sorted(WHITE)}}, {"email": 1}))
uids = [str(u["_id"]) for u in users]
for c in ("submissions", "attainments", "attempts", "resource_progress", "module_completions", "enrollments", "demo_progress", "diagnostic_results", "awards", "events"):
    db[c].delete_many({"user_id": {"$in": uids}})
db.users.delete_many({"_id": {"$in": [u["_id"] for u in users]}})
print("test accounts removed:", [u["email"] for u in users])
