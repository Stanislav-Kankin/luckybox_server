import os
from random import randint
from typing import Callable, Awaitable, Any

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, Update, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.web_app import safe_parse_webapp_init_data

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from tortoise import Tortoise
import uvicorn
import dotenv

from models import User, userpy

dotenv.load_dotenv()
WEBAPP_URL = os.getenv("WEBAPP_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


class UserMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        if not event.from_user.username:
            return await event.answer("You need to set your username to use this bot.")

        user = await User.filter(id=event.from_user.id).first()
        if not user:
            user = await User.create(id=event.from_user.id, username=event.from_user.username)

        data["user"] = user
        return await handler(event, data)


def auth(request: Request):
    try:
        auth_string = request.headers.get("Authorization", None)
        if auth_string:
            data = safe_parse_webapp_init_data(bot.token, auth_string)
            return data
        else:
            raise HTTPException(401, {"error": "Unauthorized"})
    except Exception:
        raise HTTPException(401, {"error": "Unauthorized"})


async def lifespan(app: FastAPI):
    await bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )

    await Tortoise.init(db_url=os.getenv("DB_URL"), modules={"models": ["models"]})
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
app = FastAPI(lifespan=lifespan)

markup = InlineKeyboardBuilder().button(text="LuckyBoxes", web_app=WebAppInfo(url=WEBAPP_URL)).as_markup()

dp.message.middleware(UserMiddleware())
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(f"🎁 Открывай свои боксы!", reply_markup=markup)


@app.get("/api/user", response_class=JSONResponse)
async def get_user(request: Request, auth_data: dict = Depends(auth)):
    user = await User.filter(id=auth_data.user.id).first()
    user_pydantic = await userpy.from_tortoise_orm(user)
    return JSONResponse(user_pydantic.model_dump(mode="json"))


@app.post("/api/open", response_class=JSONResponse)
async def open_box(request: Request, auth_data: dict = Depends(auth)):
    win = randint(1, 1000)

    user = await User.filter(id=auth_data.user.id).first()
    user.luckyboxes -= 1
    user.balance += win
    await user.save()

    return JSONResponse(
        {"win": win, "current_luckyboxes": user.luckyboxes, "current_balance": user.balance}
    )


@app.post("/webhook")
async def webhook(request: Request):
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    uvicorn.run(app)
