"""Classify whether a text contains the name of a politician."""

import json
import sys

import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
from pydantic import BaseModel, Field

MODEL = "gpt-5.4-nano"
SECRET_NAME = "openai-api-key"
SECRET_REGION = "us-east-2"
SECRET_KEY = "OPENAI_API_KEY"

SAMPLE_TEXTS = [
    "Angela Merkel met with business leaders in Berlin last week.",
    "The bakery on Main Street opens at 7 a.m. and sells rye bread.",
    "During the debate, Kamala Harris outlined her tax proposal.",
    "Python's asyncio library makes concurrent I/O easier to write.",
]


class PoliticianNameClassification(BaseModel):
    contains_politician_name: bool = Field(
        description="True if the text mentions a politician by name."
    )


def get_openai_api_key() -> str:
    client = boto3.client("secretsmanager", region_name=SECRET_REGION)
    try:
        response = client.get_secret_value(SecretId=SECRET_NAME)
    except ClientError as exc:
        raise SystemExit(
            f"Could not load {SECRET_NAME} from Secrets Manager: {exc}"
        ) from exc

    secret_string = response.get("SecretString")
    if not secret_string:
        raise SystemExit(f"Secret {SECRET_NAME} has no SecretString.")

    try:
        payload = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Secret {SECRET_NAME} is not valid JSON.") from exc

    api_key = payload.get(SECRET_KEY)
    if not api_key:
        raise SystemExit(f"Secret {SECRET_NAME} is missing {SECRET_KEY}.")
    return api_key


def classify_politician_name(client: OpenAI, text: str) -> PoliticianNameClassification:
    completion = client.chat.completions.parse(
        model=MODEL,
        messages=[
            {
                "role": "developer",
                "content": (
                    "Classify whether the user text contains the name of a politician. "
                    "A politician currently holds, previously held, or is a well-known "
                    "candidate for elected or appointed government office."
                ),
            },
            {"role": "user", "content": text},
        ],
        response_format=PoliticianNameClassification,
    )
    message = completion.choices[0].message
    if message.parsed is None:
        raise RuntimeError(message.refusal or "Model did not return a classification.")
    return message.parsed


def main() -> None:
    client = OpenAI(api_key=get_openai_api_key())
    texts = sys.argv[1:] or SAMPLE_TEXTS

    for text in texts:
        result = classify_politician_name(client, text)
        label = "yes" if result.contains_politician_name else "no"
        print(f"{label}\t{text}")


if __name__ == "__main__":
    main()
