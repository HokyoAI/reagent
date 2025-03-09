from .openai import OpenAI


class Groq(OpenAI):
    def __init__(self, api_key, api_base="https://api.groq.com/openai/v1"):
        super().__init__(api_key, api_base)
