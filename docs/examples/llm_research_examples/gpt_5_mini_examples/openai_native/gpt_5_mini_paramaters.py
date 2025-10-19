from litellm import get_supported_openai_params

params = get_supported_openai_params(model="gpt-5-mini")
print(params)
