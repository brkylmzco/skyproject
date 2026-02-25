from typing import List, Dict, Any, Optional


class PromptGenerator:
    """
    Class responsible for generating intelligent prompts for LLM interactions with advanced context handling.
    """

    def __init__(self, max_interactions: int = 5, max_feedbacks: int = 3):
        self.previous_interactions: List[str] = []
        self.feedback_list: List[str] = []
        self.max_interactions = max_interactions
        self.max_feedbacks = max_feedbacks

    def generate_prompt(
        self, context: Dict[str, Any], user_input: str, feedback: Optional[List[str]] = None, interactions: Optional[List[str]] = None
    ) -> str:
        """
        Generate a context-aware prompt for LLMs, dynamically adjusting based on previous interactions and feedback.

        :param context: A dictionary containing context information.
        :param user_input: The input provided by the user.
        :param feedback: Optional list of feedback from previous interactions to adjust the prompt.
        :param interactions: Optional list of previous interactions to enhance contextual understanding.
        :return: A crafted prompt string.
        """
        # Incorporate provided feedback and interactions
        self.incorporate_feedback(feedback or [])
        if interactions:
            for interaction in interactions:
                self.incorporate_interaction(interaction)

        additional_context = self._extract_additional_context(context)
        interaction_history = self._format_previous_interactions()
        feedback_context = self._format_feedback()

        prompt = (
            f"{additional_context}\n"
            f"{interaction_history}"
            f"{feedback_context}"
            f"User: {user_input}\nAI:"
        )

        # Update histories with limits
        self._update_interaction_history(user_input)
        return prompt

    def _extract_additional_context(self, context: Dict[str, Any]) -> str:
        """
        Extract and format additional context from the context dictionary.

        :param context: A dictionary containing context information.
        :return: A formatted string of additional context.
        """
        parts = []
        for key, value in context.items():
            parts.append(f"{key.capitalize()}: {value}")
        return "\n".join(parts)

    def _format_previous_interactions(self) -> str:
        """
        Format the history of previous interactions to provide context.

        :return: A formatted string of previous interactions.
        """
        if not self.previous_interactions:
            return ""

        # Prioritize recent interactions with more weight
        interactions = "\n".join(
            [
                f"Previous interaction {i + 1}: {interaction}"
                for i, interaction in enumerate(self.previous_interactions[-self.max_interactions:])
            ]
        )
        return f"{interactions}\n"

    def _format_feedback(self) -> str:
        """
        Format the feedback from previous interactions.

        :return: A formatted feedback string.
        """
        if not self.feedback_list:
            return ""

        # Include feedback with weights based on recency or frequency
        formatted_feedback = "\n".join(
            [f"Feedback {i + 1}: {fb}" for i, fb in enumerate(self.feedback_list[-self.max_feedbacks:])]
        )
        return f"{formatted_feedback}\n"

    def _update_interaction_history(self, interaction: str) -> None:
        """
        Add a new interaction to the history, ensuring the list stays within the defined limit.
        """
        self.previous_interactions.append(interaction)
        if len(self.previous_interactions) > self.max_interactions:
            self.previous_interactions.pop(0)

    def _update_feedback_list(self, feedback: str) -> None:
        """
        Add new feedback to the list, ensuring the list stays within the defined limit.
        """
        self.feedback_list.append(feedback)
        if len(self.feedback_list) > self.max_feedbacks:
            self.feedback_list.pop(0)

    def clear_history(self) -> None:
        """
        Clear the previous interactions and feedback history.
        """
        self.previous_interactions.clear()
        self.feedback_list.clear()

    def incorporate_feedback(self, feedback: List[str]) -> None:
        """
        Incorporate a list of feedback into the prompt generator, ensuring it is contextually aware.

        :param feedback: List of feedback strings to incorporate.
        """
        for fb in feedback:
            self._update_feedback_list(fb)

    def incorporate_interaction(self, interaction: str) -> None:
        """
        Incorporate a single interaction into the prompt generator, ensuring it is contextually aware.

        :param interaction: Interaction string to incorporate.
        """
        self._update_interaction_history(interaction)
