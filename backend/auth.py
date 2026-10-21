import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from core import BaseDocument, db, now_iso, logger

JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(hours=8)
REFRESH_TTL = timedelta(days=7)
ROLES = ["learner", "admin"]
ADMIN_INDEX = "unique_single_admin"
MIGRATION_ID = "2026_10_roles"
MAX_FAILED = 5
LOCK_MINUTES = 15

router = APIRouter(prefix="/api/auth", tags=["auth"])


class User(BaseDocument):
    email: str
    first_name: str
    last_name: str
    role: str = "learner"
    created_at: str
    active: bool = True
    session_version: int = 0

    @property
    def roles(self) -> List[str]:
        return [self.role]

    def public(self) -> dict:
        d = self.out()
        for k in ("password_hash", "legacy_roles", "session_version", "roles"):
            d.pop(k, None)
        d["roles"] = [self.role]
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


def make_token(user_id: str, kind: str, ttl: timedelta, sv: int) -> str:
    payload = {"sub": user_id, "type": kind, "sv": sv, "exp": datetime.now(timezone.utc) + ttl}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def issue_session(response: Response, user: User) -> dict:
    access = make_token(user.id, "access", ACCESS_TTL, user.session_version)
    refresh = make_token(user.id, "refresh", REFRESH_TTL, user.session_version)
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
    check_session(doc, payload)
    return User.from_mongo(doc)


def check_session(doc: Optional[dict], payload: dict):
    if not doc:
        raise HTTPException(401, "Utilisateur introuvable")
    if doc.get("active") is False:
        raise HTTPException(401, "Compte désactivé")
    if payload.get("sv", 0) != doc.get("session_version", 0) or doc.get("role") not in ROLES:
        raise HTTPException(401, "Session expirée. Reconnectez-vous.")


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
           "password_hash": hash_password(body.password), "role": "learner", "active": True, "session_version": 0, "created_at": now_iso()}
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
    check_session(doc, payload)
    return issue_session(response, User.from_mongo(doc))


@router.post("/forgot-password")
async def forgot_password():
    return {"message": "Contactez l'administrateur de la plateforme : contact@relaisit.com", "contact_email": "contact@relaisit.com"}


async def ensure_admin_index():
    await db.users.create_index([("role", 1)], name=ADMIN_INDEX, unique=True, partialFilterExpression={"role": "admin"})


async def insert_if_missing(email: Optional[str], password: Optional[str], first: str, last: str, role: str):
    if not email or not password or await db.users.find_one({"email": email.lower()}):
        return
    try:
        await db.users.insert_one({"email": email.lower(), "first_name": first, "last_name": last, "role": role, "active": True,
                                   "session_version": 0, "password_hash": hash_password(password), "created_at": now_iso()})
    except DuplicateKeyError:
        logger.info("Seed ignoré : %s déjà présent ou administrateur existant", role)


async def seed_users():
    await db.users.create_index("email", unique=True)
    indexes = await db.login_attempts.index_information()
    if "identifier_1" in indexes and not indexes["identifier_1"].get("unique"):
        await db.login_attempts.drop()
    await db.login_attempts.create_index("identifier", unique=True)
    if await db.users.find_one({"roles": {"$exists": True}}) and not await db.migrations.find_one({"_id": MIGRATION_ID}):
        logger.warning("Migration des rôles non appliquée : aucun compte créé au démarrage.")
        return
    await ensure_admin_index()
    if not await db.users.find_one({"role": "admin"}):
        await insert_if_missing(os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD"), "Administrateur", "CASA", "admin")
    await insert_if_missing(os.environ.get("LEARNER_EMAIL"), os.environ.get("LEARNER_PASSWORD"), "Aya", "Kouassi", "learner")
    logger.info("Users seed checked")


def require_roles(*roles):
    async def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Accès réservé.")
        return user
    return dep


async def require_learner(user: User = Depends(get_current_user)) -> User:
    if user.role != "learner":
        raise HTTPException(403, "Action réservée aux apprenants. Le compte administrateur consulte en lecture seule.")
    return user
