import json
from typing import TypeVar

from ollama import Client
from pydantic import BaseModel, ValidationError

from src.config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
)


T = TypeVar(
    "T",
    bound=BaseModel,
)


class OllamaService:

    def __init__(self) -> None:

        self.client = Client(
            host=OLLAMA_HOST
        )

        self.model = OLLAMA_MODEL

    # ========================================================
    # SIMPLE CHAT
    # ========================================================

    def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:

        messages = []

        if system_prompt:

            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": 0,
            },
        )

        return (
            response.message.content
            or ""
        )

    # ========================================================
    # STRUCTURED CHAT
    # ========================================================

    def structured_chat(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        max_attempts: int = 2,
    ) -> T:
        """
        Request structured JSON from Ollama.

        If the first response is empty, invalid JSON,
        or does not satisfy the Pydantic schema,
        automatically retry once.
        """

        base_messages = []

        if system_prompt:

            base_messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        base_messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        last_error: Exception | None = None

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            # Copy messages so retry instructions
            # do not modify the original list.
            messages = list(
                base_messages
            )

            # On retry, reinforce JSON requirements.
            if attempt > 1:

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Return ONLY one valid JSON object "
                            "matching the required schema. "
                            "Do not include markdown, commentary, "
                            "code fences, or additional text. "
                            "All confidence values must be "
                            "between 0.0 and 1.0."
                        ),
                    }
                )

            try:

                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    format=(
                        schema.model_json_schema()
                    ),
                    options={
                        "temperature": 0,
                    },
                )

                raw_content = (
                    response.message.content
                    or ""
                ).strip()

                # --------------------------------------------
                # Empty response protection
                # --------------------------------------------

                if not raw_content:

                    raise ValueError(
                        "LLM returned an empty response."
                    )

                # --------------------------------------------
                # JSON parsing
                # --------------------------------------------

                payload = json.loads(
                    raw_content
                )

                # --------------------------------------------
                # Defensive numeric normalization
                # --------------------------------------------

                payload = (
                    self._normalize_numeric_fields(
                        payload
                    )
                )

                # --------------------------------------------
                # Pydantic validation
                # --------------------------------------------

                return schema.model_validate(
                    payload
                )

            except (
                json.JSONDecodeError,
                ValidationError,
                ValueError,
            ) as exc:

                last_error = exc

                print(
                    "[OllamaService] "
                    "Structured output failed "
                    f"(attempt {attempt}/{max_attempts}): "
                    f"{exc}"
                )

        # ====================================================
        # ALL ATTEMPTS FAILED
        # ====================================================

        raise RuntimeError(
            "Unable to obtain valid structured "
            f"output from Ollama after "
            f"{max_attempts} attempts. "
            f"Last error: {last_error}"
        )

    # ========================================================
    # OUTPUT NORMALIZATION
    # ========================================================

    @classmethod
    def _normalize_numeric_fields(
        cls,
        value,
    ):
        """
        Recursively normalize numeric fields
        returned by the local LLM.

        Example:

            confidence = 95

        becomes:

            confidence = 0.95
        """

        if isinstance(
            value,
            dict,
        ):

            normalized = {}

            for key, item in value.items():

                item = (
                    cls._normalize_numeric_fields(
                        item
                    )
                )

                if (
                    key.lower()
                    == "confidence"
                ):

                    item = (
                        cls._normalize_confidence(
                            item
                        )
                    )

                normalized[key] = item

            return normalized

        if isinstance(
            value,
            list,
        ):

            return [
                cls._normalize_numeric_fields(
                    item
                )
                for item in value
            ]

        return value

    # ========================================================
    # CONFIDENCE NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_confidence(
        value,
    ):
        """
        Normalize confidence to the [0, 1] range.

        Examples:

            0.95  -> 0.95
            "95%" -> 0.95
            95    -> 0.95
            1.2   -> 1.0
        """

        # ----------------------------------------------------
        # String values
        # ----------------------------------------------------

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            # Example: "95%"
            if value.endswith("%"):

                try:

                    numeric_value = float(
                        value[:-1]
                    )

                    return max(
                        0.0,
                        min(
                            1.0,
                            numeric_value / 100,
                        ),
                    )

                except ValueError:

                    return value

            try:

                value = float(
                    value
                )

            except ValueError:

                return value

        # ----------------------------------------------------
        # Numeric values
        # ----------------------------------------------------

        if isinstance(
            value,
            (int, float),
        ):

            numeric_value = float(
                value
            )

            # Already valid
            if (
                0.0
                <= numeric_value
                <= 1.0
            ):

                return numeric_value

            # Slight invalid overflow such as 1.1 / 1.2.
            # Treat it conservatively as maximum confidence.
            if (
                1.0
                < numeric_value
                <= 2.0
            ):

                return 1.0

            # Percentage-like output:
            # 95 -> 0.95
            if (
                2.0
                < numeric_value
                <= 100.0
            ):

                return (
                    numeric_value
                    / 100
                )

            # Extreme malformed values
            return max(
                0.0,
                min(
                    1.0,
                    numeric_value,
                ),
            )

        return value