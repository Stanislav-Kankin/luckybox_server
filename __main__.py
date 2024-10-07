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

"""Инициируем переменные окружения из .env"""
dotenv.load_dotenv()
WEBAPP_URL = os.getenv("WEBAPP_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


class UserMiddleware(BaseMiddleware):
    """Функция используется для обработки сообщений
    от пользователей и добавления информации о пользователе
    в данные, передаваемые в следующий обработчик.
    Внутри функции проверяется, установлено ли имя пользователя.
    Если имя пользователя не установлено, функция отвечает
    сообщением "You need to set your username to use this bot.".
    Затем функция пытается найти пользователя в базе данных.
    Если пользователь не найден, он создается с использованием
    идентификатора и имени пользователя. Информация о
    пользователе затем добавляется в данные, передаваемые
    в следующий обработчик."""

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
    """Функция auth используется для аутентификации пользователя.
    Внутри функции извлекается строка авторизации из заголовков запроса.
    Если строка авторизации присутствует, функция пытается разобрать
    данные инициализации бота с использованием токена и строки авторизации.
    Если разбор данных проходит успешно, функция возвращает разобранные данные.
    Если строка авторизации отсутствует или разбор данных не удается,
    функция генерирует исключение HTTPException с кодом 401
    и сообщением "Unauthorized"."""
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
    """Функция lifespan используется для установки вебхука
    для бота и инициализации базы данных.
    Внутри функции устанавливается вебхук для бота с
    использованием URL-адреса, указанного в переменной
    WEBHOOK_URL, и разрешенных обновлений, определенных в
    диспетчере dp. Затем функция инициализирует базу
    данных с использованием URL-адреса, полученного из
    переменной окружения DB_URL, и модулей, указанных в
    списке modules. После этого функция генерирует схемы
    для базы данных. Наконец, функция закрывает все
    соединения с базой данных."""
    await bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )

    await Tortoise.init(db_url=os.getenv("DB_URL"), modules={"models": ["models"]})
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()

"""Создаем бота и приложение в FastAPI"""
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
app = FastAPI(lifespan=lifespan)

"""Инлайн клавиатура"""
markup = InlineKeyboardBuilder().button(text="LuckyBoxes", web_app=WebAppInfo(url=WEBAPP_URL)).as_markup()

"""В этом коде используется встроенное в
aiogram средство обработки UserMiddleware для
обработки сообщений от пользователей и добавления
информации о пользователе в данные, передаваемые
в следующий обработчик. Затем создается экземпляр
приложения FastAPI с использованием кормиджа
CORSMiddleware для обработки запросов с различными источниками,
учетными данными, методами и заголовками. Этот
экземпляр приложения затем добавляется в
диспетчер dp для обработки сообщений от пользователей."""

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
    """Функция start обрабатывает команду '/start' и отвечает
    сообщением с паролем для открытия боксов.
    Внутри функции генерируется сообщение с паролем,
    который пользователь может скопировать, нажав на него.
    Затем функция отвечает сообщением с
    текстом "🎁 Открывай свои боксы!".
    Этот текст отображается с использованием разметки markup."""

    await message.answer(
        "Чтобы открыть боксы тебе понадобиться пароль ниже.\n"
        "<code>147.45.193.130</code> нажми на него и он скопируется!\n"
        "🎁 Открывай свои боксы!", reply_markup=markup
        )


@app.get("/api/user", response_class=JSONResponse)
async def get_user(request: Request, auth_data: dict = Depends(auth)):
    """Функция get_user обрабатывает GET-запрос к
    эндпоинту '/api/user' и возвращает информацию
    о пользователе в формате JSON. Внутри функции
    извлекается информация о пользователе из базы
    данных с использованием идентификатора пользователя,
    полученного из данных авторизации. Затем информация
    о пользователе преобразуется в объект Pydantic
    с использованием функции from_tortoise_orm.
    Наконец, функция возвращает ответ в формате JSON
    с использованием класса JSONResponse."""

    user = await User.filter(id=auth_data.user.id).first()
    user_pydantic = await userpy.from_tortoise_orm(user)
    return JSONResponse(user_pydantic.model_dump(mode="json"))


@app.post("/api/open", response_class=JSONResponse)
async def open_box(request: Request, auth_data: dict = Depends(auth)):
    """Функция open_box обрабатывает POST-запрос к
    эндпоинту '/api/open' и возвращает информацию о
    выигрыше и обновленной информации о пользователе.
    Внутри функции генерируется случайное число от 1 до 1000,
    которое используется в качестве выигрыша.
    Затем информация о пользователе извлекается из базы
    данных с использованием идентификатора пользователя,
    полученного из данных авторизации.
    Количество боксов пользователя уменьшается на 1,
    а его баланс увеличивается на выигрыш.
    После этого информация о пользователе сохраняется в базе данных.
    Наконец, функция возвращает ответ в формате
    JSON с использованием класса JSONResponse."""

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
    """Функция webhook обрабатывает POST-запрос
    к эндпоинту '/webhook' и передает обновление в диспетчер dp.
    Внутри функции извлекается обновление из тела запроса с
    использованием функции model_validate. Затем обновление
    передается в диспетчер dp для обработки."""

    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
