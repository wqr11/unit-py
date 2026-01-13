from os import getenv
from dotenv import load_dotenv

from openai import OpenAI
from .prompt import prompt

_ = load_dotenv()

OPENAI_BASE_URL = str(getenv("OPENAI_BASE_URL"))
OPENAI_API_KEY = str(getenv("OPENAI_API_KEY"))


class ChatService:
    def __init__(self, base_url: str, api_key: str):
        self.client: OpenAI = OpenAI(base_url=base_url, api_key=api_key) if (base_url or api_key) else None

    
    def validate_task(self, text: str):
        if client == None:
            return {"output_text": "[Ошибка] Не удалось инициализировать ИИ клиент"}
        res = self.client.responses.create(
            model="gpt-4.1-nano", input=f"{prompt}\n{text}"
        )
        return res.to_dict()


client = ChatService(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)