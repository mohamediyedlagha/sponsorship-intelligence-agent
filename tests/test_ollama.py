from pydantic import BaseModel

from src.services.ollama_service import OllamaService


class OllamaResult(BaseModel):
    status: str
    message: str


def test_ollama_text_connection():

    llm = OllamaService()

    response = llm.chat(
        prompt=(
            "Return exactly the words: "
            "LOCAL LLM WORKING"
        )
    )

    assert response


def test_ollama_structured_output():

    llm = OllamaService()

    response = llm.structured_chat(
        prompt="""
        Return a test result.

        status must be "success".

        Explain briefly that the local
        LLM connection works.
        """,
        schema=OllamaResult,
    )

    assert response.status == "success"

    print(response)