from skyproject.shared.exceptions import JSONDecodeError, CoderError

class Coder:
    ...

    async def implement(self, task: Task) -> list[CodeChange]:
        try:
            ...
        except json.JSONDecodeError as e:
            logger.error('JSON Decode Error - Failed to decode JSON response: %s', str(e), exc_info=True)
            raise JSONDecodeError('Failed to decode JSON response from LLM', e)
        except Exception as e:
            logger.error('Coder Error - Error implementing task: %s', str(e), exc_info=True)
            raise CoderError('Unexpected error in code implementation', e)

    async def improve_from_feedback(
        self, task: Task, feedback: str, suggestions: list[str]
    ) -> list[CodeChange]:
        try:
            ...
        except json.JSONDecodeError as e:
            logger.error('JSON Decode Error - Failed to decode JSON response: %s', str(e), exc_info=True)
            raise JSONDecodeError('Failed to decode JSON response from LLM', e)
        except Exception as e:
            logger.error('Coder Error - Error improving task from feedback: %s', str(e), exc_info=True)
            raise CoderError('Unexpected error in feedback improvement', e)