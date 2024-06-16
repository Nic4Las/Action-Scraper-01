from typing import List
from pydantic import BaseModel
from .Labels import Labels


class NovelData(BaseModel):
    title: str
    fiction_id: str
    link: str
    tags: List[str]
    lable: Labels
    following_count: int
    rating: float
    page_count: int
    view_count: int
    chapters_count: int
    last_update: int
    description: str
    description_hash: int
