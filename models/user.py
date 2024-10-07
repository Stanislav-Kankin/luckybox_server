from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator


class User(Model):
    """Класс User является моделью в Tortoise ORM.
    Внутри класса определены поля id, username,
    luckyboxes и balance. Поле id является первичным
    ключом и не может быть null. Поле username может
    быть null и имеет максимальную длину в 32 символа.
    Поля luckyboxes и balance имеют значения по
    умолчанию 1 и 0 соответственно. Эти поля используются
    для хранения информации о пользователе в базе данных."""
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=32, null=True)
    luckyboxes = fields.IntField(default=1)
    balance = fields.IntField(default=0)


userpy = pydantic_model_creator(User)
