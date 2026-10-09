import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from core import BaseDocument, db, now_iso, logger

JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(hours=8)
REFRESH_TTL = timedelta(days=7)
ROLES = ["learner", "author", "reviewer", "evaluator", "pedagogical_lead", "admin"]
MAX_FAILED = 5
LOCK_MINUTES = 15

router = APIRouter(prefix="/api/auth", tags=["auth"])


class User(BaseDocument):
    email: str
    first_name: str
    last_name: str
    roles: List[str]
    created_at: str
    active: bool = True

    def public(self) -> dict:
        d = self.out()
        d.pop("password_hash", None)
        return d


class RegisterIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def make_token(user_id: str, kind: str, ttl: timedelta) -> str:
    payload = {"sub": user_id, "type": kind, "exp": datetime.now(timezone.utc) + ttl}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def issue_session(response: Response, user: User) -> dict:
    access = make_token(user.id, "access", ACCESS_TTL)
    refresh = make_token(user.id, "refresh", REFRESH_TTL)
    opts = dict(httponly=True, secure=True, samesite="none", path="/")
    response.set_cookie("access_token", access, max_age=int(ACCESS_TTL.total_seconds()), **opts)
    response.set_cookie("refresh_token", refresh, max_age=int(REFRESH_TTL.total_seconds()), **opts)
    return {"user": user.public(), "access_token": access, "token_type": "bearer"}


def read_token(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return request.cookies.get("access_token")


async def user_from_token(token: str) -> User:
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(401, "Session invalide")
        doc = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expirée")
    except (jwt.InvalidTokenError, InvalidId):
        raise HTTPException(401, "Session invalide")
    if not doc:
        raise HTTPException(401, "Utilisateur introuvable")
    if doc.get("active") is False:
        raise HTTPException(401, "Compte désactivé")
    return User.from_mongo(doc)


async def get_current_user(request: Request) -> User:
    token = read_token(request)
    if not token:
        raise HTTPException(401, "Connexion requise")
    return await user_from_token(token)


async def get_optional_user(request: Request) -> Optional[User]:
    token = read_token(request)
    if not token:
        return None
    try:
        return await user_from_token(token)
    except HTTPException:
        return None


@router.post("/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Un compte existe déjà avec cette adresse e-mail.")
    doc = {"email": email, "first_name": body.first_name.strip(), "last_name": body.last_name.strip(),
           "password_hash": hash_password(body.password), "roles": ["learner"], "created_at": now_iso()}
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    return issue_session(response, User.from_mongo(doc))


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ident = email
    attempt = await db.login_attempts.find_one({"identifier": ident})
    now = datetime.now(timezone.utc)
    if attempt and attempt.get("locked_until") and datetime.fromisoformat(attempt["locked_until"]) > now:
        raise HTTPException(429, "Trop de tentatives. Réessayez dans 15 minutes.")
    doc = await db.users.find_one({"email": email})
    if not doc or not verify_password(body.password, doc["password_hash"]):
        count = (attempt or {}).get("count", 0) + 1
        update = {"identifier": ident, "count": count}
        if count >= MAX_FAILED:
            update = {"identifier": ident, "count": 0, "locked_until": (now + timedelta(minutes=LOCK_MINUTES)).isoformat()}
        await db.login_attempts.update_one({"identifier": ident}, {"$set": update}, upsert=True)
        raise HTTPException(401, "Adresse e-mail ou mot de passe incorrect.")
    await db.login_attempts.delete_many({"identifier": ident})
    if doc.get("active") is False:
        raise HTTPException(403, "Ce compte est désactivé. Contactez l'administrateur de la plateforme.")
    return issue_session(response, User.from_mongo(doc))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return user.public()


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Session expirée")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Session invalide")
        doc = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    except (jwt.InvalidTokenError, InvalidId):
        raise HTTPException(401, "Session invalide")
    if not doc or doc.get("active") is False:
        raise HTTPException(401, "Utilisateur introuvable")
    return issue_session(response, User.from_mongo(doc))


@router.post("/forgot-password")
async def forgot_password():
    return {"message": "La réinitialisation automatique n'est pas encore disponible. Contactez l'administrateur de la plateforme pour obtenir un nouveau mot de passe."}


async def seed_user(email: str, password: str, first: str, last: str, roles: List[str]):
    email = email.lower()
    existing = await db.users.find_one({"email": email})
    if existing is None:
        await db.users.insert_one({"email": email, "first_name": first, "last_name": last, "roles": roles,
                                   "password_hash": hash_password(password), "created_at": now_iso()})
    elif not verify_password(password, existing["password_hash"]):
        await db.users.update_one({"_id": existing["_id"]}, {"$set": {"password_hash": hash_password(password)}})


async def seed_users():
    await db.users.create_index("email", unique=True)
    indexes = await db.login_attempts.index_information()
    if "identifier_1" in indexes and not indexes["identifier_1"].get("unique"):
        await db.login_attempts.drop()
    await db.login_attempts.create_index("identifier", unique=True)
    await seed_user(os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"], "Administrateur", "CASA", ["admin", "learner"])
    await seed_user(os.environ["LEARNER_EMAIL"], os.environ["LEARNER_PASSWORD"], "Aya", "Kouassi", ["learner"])
    await seed_user(os.environ["EVALUATOR_EMAIL"], os.environ["EVALUATOR_PASSWORD"], "Koffi", "N'Guessan", ["evaluator"])
    await seed_user(os.environ["AUTHOR_EMAIL"], os.environ["AUTHOR_PASSWORD"], "Awa", "Traoré", ["author"])
    await seed_user(os.environ["REVIEWER_EMAIL"], os.environ["REVIEWER_PASSWORD"], "Yao", "Konan", ["reviewer"])
    await seed_user(os.environ["LEAD_EMAIL"], os.environ["LEAD_PASSWORD"], "Mariam", "Diabaté", ["pedagogical_lead"])
    logger.info("Users seeded")


def require_roles(*roles):
    async def dep(user: User = Depends(get_current_user)) -> User:
        if not set(roles) & set(user.roles):
            raise HTTPException(403, "Accès réservé.")
        return user
    return dep
