"""Previous-version completion label: isolated database (QA-ROLE-), dropped afterwards."""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from creds import ADMIN  # noqa: F401  (loads backend/.env)
from motor.motor_asyncio import AsyncIOMotorClient

import core
import learning

ISO = os.environ["DB_NAME"] + "_qa_role_prevcompl"
MID, UID = "QA-ROLE-M", "qa-role-learner-prev"


def version_doc(v, rule):
    return {"_id": f"{MID}@{v}", "entity_id": MID, "version": v, "status": "published" if v == 2 else "retired", "code": "QA", "title": "QA-ROLE module",
            "summary": "", "levels": ["L0"], "layer_ids": [], "stage_ids": [], "competency_ids": [], "concept_ids": [], "objectives": [], "prerequisites": [],
            "prerequisite_module_ids": [], "resource_ids": ["QA-ROLE-R1"], "duration_hours": 1, "changelog": "QA-ROLE", "approved": True, "created_at": datetime.now(timezone.utc).isoformat(),
            **({"completion_rule": rule} if rule else {})}


async def scenario():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[ISO]
    saved = core.db, learning.db
    core.db = learning.db = db
    try:
        await db.modules.insert_one({"_id": MID, "code": "QA", "published_version": 2, "latest_version": 2, "created_at": "2026-10-01", "updated_at": "2026-10-01"})
        await db.module_versions.insert_many([version_doc(1, "resources"), version_doc(2, "resources_and_graded")])
        await db.resource_progress.insert_one({"user_id": UID, "resource_id": "QA-ROLE-R1", "module_id": MID, "completed_at": "2026-10-01"})
        await db.module_completions.insert_one({"user_id": UID, "module_id": MID, "module_version": 1, "completed_at": "2026-10-01"})
        before = await db.module_completions.find_one({"user_id": UID}, {"_id": 0})
        prog = await learning.module_progress(UID, MID)
        after = await db.module_completions.find_one({"user_id": UID}, {"_id": 0})
        fresh = await learning.module_progress("qa-role-other", MID)
        await db.attempts.insert_one({"user_id": UID, "assessment_id": f"A-{MID}-G", "module_id": MID, "passed": True, "percent": 1, "created_at": "2026-10-02"})
        passed = await learning.module_progress(UID, MID)
        return prog, before, after, fresh, passed
    finally:
        core.db, learning.db = saved
        await db.client.drop_database(ISO)


def test_previous_completion_label_isolated():
    prog, before, after, fresh, passed = asyncio.run(scenario())
    assert prog["status"] == "in_progress" and prog["module_version"] == 2
    assert prog["previous_completion"] == {"version": 1, "completed_at": "2026-10-01"}
    assert before == after
    assert fresh["previous_completion"] is None
    assert passed["status"] == "completed" and passed["previous_completion"] is None
    from pymongo import MongoClient
    assert ISO not in MongoClient(os.environ["MONGO_URL"]).list_database_names()
