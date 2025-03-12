class Prompt:
    def __init__(self, prompt: str):
        self.prompt = prompt

    def __call__(self, *args, **kwargs):
        self.prompt.format(*args, **kwargs)
