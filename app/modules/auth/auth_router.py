import json
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.users.user_schema import CreateUser
from app.modules.users.user_service import UserService
from app.modules.utils.APIRouter import APIRouter
from app.modules.utils.posthog_helper import PostHogClient

auth_router = APIRouter()
load_dotenv(override=True)


class AuthAPI:
    @auth_router.post("/signup")
    async def signup(request: Request, db: Session = Depends(get_db)):
        body = json.loads(await request.body())
        uid = body["uid"]
        user_service = UserService(db)
        user = user_service.get_user_by_uid(uid)
        if user:
            message, error = user_service.update_last_login(uid)
            if error:
                return Response(content=message, status_code=400)
            else:
                return Response(content=json.dumps({"uid": uid}), status_code=200)
        else:
            first_login = datetime.utcnow()
            user = CreateUser(
                uid=uid,
                email=body["email"],
                display_name=body["displayName"],
                email_verified=body["emailVerified"],
                created_at=first_login,
                last_login_at=first_login,
                provider_info=body["providerData"][0],
                provider_username=body["providerUsername"],
            )
            uid, message, error = user_service.create_user(user)
            PostHogClient().send_event(
                uid,
                "signup_event",
                {
                    "email": body["email"],
                    "display_name": body["displayName"],
                    "github_username": body["providerUsername"],
                },
            )
            if error:
                return Response(content=message, status_code=400)
            return Response(content=json.dumps({"uid": uid}), status_code=201)
