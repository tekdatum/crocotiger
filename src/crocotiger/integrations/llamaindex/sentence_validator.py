from crocotiger_engine import SentenceValidator
from llama_index.core.base.response.schema import Response
from llama_index.core.llms import LLM
from llama_index.core.query_engine import CustomQueryEngine


class SentenceValidatorLLMGuard(CustomQueryEngine):
    """Guardrail that validates a prompt and blocks it before it ever reaches the LLM."""

    llm: LLM
    sentence_validator: SentenceValidator

    model_config = {"arbitrary_types_allowed": True}

    async def acustom_query(self, query_str: str) -> Response:
        result = await self.sentence_validator.validate(query_str)

        if not result.valid:
            return Response(
                response="Request blocked: ...",
                metadata={"validation_result": result},
            )

        completion = await self.llm.acomplete(query_str)
        return Response(
            response=str(completion),
            metadata={"validation_result": result},
        )

    def custom_query(self, query_str: str) -> Response:
        import asyncio

        return asyncio.run(self.acustom_query(query_str))
