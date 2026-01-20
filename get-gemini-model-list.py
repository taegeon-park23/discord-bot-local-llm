from openai import OpenAI

client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key="YOUR_GEMINI_API_KEY")
models = client.models.list()
for model in models:
    print(model.id)