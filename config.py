from dataclasses import dataclass
from typing import Optional
from environs import Env

@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту

@dataclass
class Config:
    tg_bot: TgBot
    hf_api_key: str

def load_config(path: Optional[str] = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        tg_bot=TgBot(token=env('BOT_TOKEN')),
        hf_api_key=env('HF_API_KEY')
    )