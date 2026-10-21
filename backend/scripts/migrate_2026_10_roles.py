"""Role consolidation migration (admin + learner). Dry-run by default; --apply writes, --index creates the single-admin index."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from core import db, now_iso  # noqa: E402
from auth import ADMIN_INDEX, MIGRATION_ID  # noqa: E402

OLD_ADMIN, NEW_ADMIN = "admin@casa-academy.ci", "admin@casa-academy.com"
RETIRED_STAFF = {"evaluator@casa-academy.ci", "author@casa-academy.ci", "reviewer@casa-academy.ci", "lead@casa-academy.ci"}


def plan_for(doc: dict) -> dict:
    legacy = doc.get("roles")
    target = {"role": "learner"}
    if doc["email"] in (OLD_ADMIN, NEW_ADMIN):
        target = {"role": "admin", "email": NEW_ADMIN, "active": True}
    elif doc["email"] in RETIRED_STAFF:
        target = {"role": "learner", "active": False}
    changes = {k: v for k, v in target.items() if doc.get(k, True if k == "active" else None) != v}
    if legacy is not None:
        changes["legacy_roles"] = legacy
    privileged = bool(set(legacy or doc.get("legacy_roles") or []) - {"learner"})
    bump = bool(changes) and (privileged or "email" in changes or changes.get("active") is False)
    return {"changes": changes, "unset_roles": legacy is not None, "bump": bump}


async def run(apply: bool, index: bool):
    users = await db.users.find({}, {"password_hash": 0}).to_list(10000)
    plans = [(u, plan_for(u)) for u in users]
    todo = [(u, p) for u, p in plans if p["changes"] or p["unset_roles"]]
    admins = [u for u, p in plans if p["changes"].get("role", u.get("role")) == "admin"]
    report = {"users": len(users), "to_update": len(todo), "target_admins": [a.get("email") for a in admins],
              "privileged_updates": [{"email": u["email"], "changes": {k: v for k, v in p["changes"].items()}, "session_bump": p["bump"]}
                                     for u, p in todo if p["bump"]]}
    if len(admins) != 1:
        raise SystemExit(f"Abandon : {len(admins)} administrateur(s) cible(s), 1 attendu.")
    print(json.dumps({"mode": "apply" if apply else "dry-run", **report}, ensure_ascii=False, indent=1))
    if apply and todo:
        for u, p in todo:
            update = {"$set": p["changes"]} if p["changes"] else {}
            if p["unset_roles"]:
                update["$unset"] = {"roles": ""}
            if p["bump"]:
                update["$inc"] = {"session_version": 1}
            await db.users.update_one({"_id": u["_id"]}, update)
            if p["bump"]:
                await db.catalog_change_log.insert_one({"at": now_iso(), "user_id": None, "user_email": "migration-2026-10-roles", "user_name": "Migration des rôles",
                                                        "entity_type": "user", "entity_id": p["changes"].get("email", u["email"]), "version": None,
                                                        "action": "role_migration", "details": f"rôles hérités {u.get('roles')} → {p['changes'].get('role', u.get('role'))}"
                                                        + (" ; email modifié" if "email" in p["changes"] else "") + (" ; compte désactivé" if p["changes"].get("active") is False else "")})
        await db.users.update_many({"role": {"$exists": False}}, {"$set": {"role": "learner"}})
        await db.users.update_many({"session_version": {"$exists": False}}, {"$set": {"session_version": 0}})
        await db.login_attempts.delete_many({"identifier": OLD_ADMIN})
        await db.migrations.update_one({"_id": MIGRATION_ID}, {"$setOnInsert": {"applied_at": now_iso(), "report": report}, "$push": {"runs": {"at": now_iso(), "updated": len(todo)}}}, upsert=True)
    elif apply:
        await db.migrations.update_one({"_id": MIGRATION_ID}, {"$push": {"runs": {"at": now_iso(), "updated": 0}}})
        print("Aucune modification : migration déjà appliquée.")
    if index:
        await db.users.create_index([("role", 1)], name=ADMIN_INDEX, unique=True, partialFilterExpression={"role": "admin"})
        print("Index", ADMIN_INDEX, "présent ; administrateurs :", await db.users.count_documents({"role": "admin"}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--index", action="store_true")
    a = ap.parse_args()
    asyncio.run(run(a.apply, a.index))
