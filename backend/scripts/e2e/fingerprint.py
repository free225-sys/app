"""Read-only fingerprint of a database: counts per collection + SHA-256 of documents of key collections."""
import hashlib
import json
import os
import sys

from bson import encode
from bson.codec_options import CodecOptions
from bson.raw_bson import RawBSONDocument
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env", override=False)
KEY = ["users", "questions", "attainments", "attempts", "awards", "enrollments", "module_completions", "resource_progress", "catalog_change_log"]


def fingerprint(db_name: str) -> dict:
    db = MongoClient(os.environ["MONGO_URL"])[db_name]
    names = sorted(db.list_collection_names())
    counts = {c: db[c].count_documents({}) for c in names}
    hashed = {}
    for c in sorted(set(KEY + [n for n in names if n.endswith("_versions")])):
        h = hashlib.sha256()
        coll = db.get_collection(c, codec_options=CodecOptions(document_class=RawBSONDocument))
        for d in coll.find({}).sort("_id", 1):
            h.update(d.raw)
        hashed[c] = h.hexdigest()
    return {"db": db_name, "counts": counts, "sha256": hashed}


if __name__ == "__main__":
    db_name, out = sys.argv[1], sys.argv[2]
    fp = fingerprint(db_name)
    with open(out, "w") as f:
        json.dump(fp, f, indent=1, sort_keys=True)
    os.chmod(out, 0o600)
    print(json.dumps({"db": db_name, "collections": len(fp["counts"]), "documents": sum(fp["counts"].values()),
                      "sha256": {k: v[:12] for k, v in fp["sha256"].items()}}, ensure_ascii=False))
