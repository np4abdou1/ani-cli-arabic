from dataclasses import dataclass

@dataclass
class AnimeResult:
    id: str
    title_en: str
    title_jp: str
    type: str
    episodes: str
    status: str
    genres: str
    mal_id: str
    relation_id: str
    score: str
    rank: str
    popularity: str
    rating: str
    premiered: str
    creators: str
    duration: str
    thumbnail: str

@dataclass
class Episode:
    number: str
    type: str
    display_num: int

@dataclass
class QualityOption:
    name: str
    server_key: str
    style: str
