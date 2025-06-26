import inspect
from typing import Optional

import pymongo
from bson import ObjectId
from flask import Flask

from bll.bll_base import BllBase
from eb_utils.configs import WebPaths
from entity.favorite_model import FavoriteModel
from entity.news_class_model import NewsClassModel
from signals import class_saving, content_saved


class Favorite(BllBase[FavoriteModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)
    def new_instance(self) -> FavoriteModel:
        return FavoriteModel()

