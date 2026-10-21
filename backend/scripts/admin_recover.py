"""Server-side admin access recovery. The password is read interactively (or from stdin), never from arguments."""
import argparse
import asyncio
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from core import db, now_iso  # noqa: E402
from auth import ensure_admin_index, hash_password  # noqa: E402


def read_password() -> str:
    if sys.stdin.isatty():
        pwd = getpass.getpass("Nouveau mot de passe : ")
        if pwd != getpass.getpass("Confirmation : "):
            raise SystemExit("Les mots de passe ne correspondent pas.")
    else:
        pwd = sys.stdin.readline().rstrip("\n")
    if len(pwd) < 8:
        raise SystemExit("Mot de passe trop court (8 caractères minimum).")
    return pwd


async def log(email: str, details: str):
    await db.catalog_change_log.insert_one({"at": now_iso(), "user_id": None, "user_email": "cli-admin-recover", "user_name": "Récupération serveur",
                                            "entity_type": "user", "entity_id": email, "version": None, "action": "admin_recover", "details": details})


async def run(email: str, set_password: bool, dry_run: bool):
    email = email.lower()
    target = await db.users.find_one({"email": email})
    if not target:
        raise SystemExit("Compte introuvable : créez d'abord un compte apprenant pour cette adresse, puis relancez.")
    current = await db.users.find_one({"role": "admin"})
    print(f"Cible : {email} (rôle {target.get('role')}) ; administrateur actuel : {current['email'] if current else 'aucun'}")
    if dry_run:
        return
    pwd = read_password() if set_password else None
    await ensure_admin_index()
    if current and current["_id"] != target["_id"]:
        await db.users.update_one({"_id": current["_id"]}, {"$set": {"role": "learner"}, "$inc": {"session_version": 1}})
        await log(current["email"], "administrateur rétrogradé en apprenant (transfert)")
    update = {"role": "admin", "active": True}
    if pwd:
        update["password_hash"] = hash_password(pwd)
    await db.users.update_one({"_id": target["_id"]}, {"$set": update, "$inc": {"session_version": 1}})
    await db.login_attempts.delete_many({"identifier": email})
    await log(email, "accès administrateur rétabli" + (" ; mot de passe redéfini" if pwd else ""))
    print("Terminé. Les sessions existantes de ce compte sont invalidées.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--set-password", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    asyncio.run(run(a.email, a.set_password, a.dry_run))
