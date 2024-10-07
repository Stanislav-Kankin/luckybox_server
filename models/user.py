from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator


class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=32, null=True)
    luckyboxes = fields.IntField(default=1)
    balance = fields.IntField(default=0)


userpy = pydantic_model_creator(User)
