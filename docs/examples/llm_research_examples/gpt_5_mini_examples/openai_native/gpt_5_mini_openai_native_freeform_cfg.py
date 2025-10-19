#WORKING CORRECTLY
import os
import textwrap
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------------------------------------------------------
print("="*80)
print("1) Freeform Function Calling — SQL")
print("="*80)

resp_sql = client.responses.create(
    model="gpt-5-mini",
    input="Write an SQL query to select all users older than 30.",
    text={"format": {"type": "text"}},  # Freeform: just raw text, no JSON wrapping
)

print(resp_sql.output_text)

# -----------------------------------------------------------------------------
print("="*80)
print("1b) Freeform Function Calling — Python")
print("="*80)

resp_py = client.responses.create(
    model="gpt-5-mini",
    input="Write a Python function to compute factorial with input validation.",
    text={"format": {"type": "text"}},
)

print(resp_py.output_text)

# -----------------------------------------------------------------------------
print("="*80)
print("2) CFG with Regex — Timestamp")
print("="*80)

timestamp_grammar = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]) (?:[01]\d|2[0-3]):[0-5]\d$"

resp_regex = client.responses.create(
    model="gpt-5-mini",
    input="Call the timestamp_grammar to produce a timestamp for August 7th 2025 at 10AM.",
    text={"format": {"type": "text"}},
    tools=[
        {
            "type": "custom",
            "name": "timestamp_grammar",
            "description": "Saves a timestamp in 'YYYY-MM-DD HH:MM' 24-hour format.",
            "format": {"type": "grammar", "syntax": "regex", "definition": timestamp_grammar},
        }
    ],
    parallel_tool_calls=False,
)

print("Timestamp:", resp_regex.output[1].input)

# -----------------------------------------------------------------------------
print("="*80)
print("3) CFG with Lark — Arithmetic Expression")
print("="*80)

arithmetic_grammar = textwrap.dedent(r"""
    start: expr
    expr: term (("+"|"-") term)*
    term: NUMBER (("*"|"/") NUMBER)*
    NUMBER: /[0-9]+/
    %ignore " "
""")

resp_lark = client.responses.create(
    model="gpt-5-mini",
    input="Call the arithmetic_grammar to generate a valid arithmetic expression using numbers 1 to 5.",
    text={"format": {"type": "text"}},
    tools=[
        {
            "type": "custom",
            "name": "arithmetic_grammar",
            "description": "Generates valid arithmetic expressions with +, -, *, / and integers.",
            "format": {"type": "grammar", "syntax": "lark", "definition": arithmetic_grammar},
        }
    ],
    parallel_tool_calls=False,
)

print("Arithmetic expression:", resp_lark.output[1].input)
