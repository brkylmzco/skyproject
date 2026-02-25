import pytest
from skyproject.shared.prompt_generation import PromptGenerator

@pytest.fixture
def prompt_generator() -> PromptGenerator:
    """Fixture to provide a PromptGenerator instance."""
    return PromptGenerator()


def test_generate_prompt_with_context(prompt_generator: PromptGenerator) -> None:
    """Test generating a prompt with provided context."""
    context = {
        "location": "office",
        "time": "morning",
    }
    user_input = "What's the agenda for today?"
    expected_output = (
        "Location: office\nTime: morning\nUser: What's the agenda for today?\nAI:"
    )
    generated_prompt = prompt_generator.generate_prompt(context, user_input)
    assert generated_prompt == expected_output


def test_generate_prompt_with_empty_context(prompt_generator: PromptGenerator) -> None:
    """Test generating a prompt without any context."""
    context = {}
    user_input = "Hello, how are you?"
    expected_output = "User: Hello, how are you?\nAI:"
    generated_prompt = prompt_generator.generate_prompt(context, user_input)
    assert generated_prompt == expected_output


def test_generate_prompt_with_feedback_and_interactions(prompt_generator: PromptGenerator) -> None:
    """Test generating a prompt with feedback and previous interactions."""
    context = {"mood": "happy"}
    user_input = "What's the weather like today?"
    feedback = "The previous response was too vague."
    prompt_generator.previous_interactions = ["How are you doing today?"]
    prompt_generator.feedback_list = ["Could be more specific."]
    expected_output = (
        "Mood: happy\n"
        "Previous interaction 1: How are you doing today?\n"
        "Feedback 1: Could be more specific.\n"
        "Feedback 2: The previous response was too vague.\n"
        "User: What's the weather like today?\nAI:"
    )
    generated_prompt = prompt_generator.generate_prompt(context, user_input, feedback)
    assert generated_prompt == expected_output


def test_generate_prompt_dynamic_and_capped_feedback(prompt_generator: PromptGenerator) -> None:
    """Test generating prompt with dynamic and capped feedback."""
    context = {}
    user_input = "Tell me a joke."
    feedbacks = ["Too long.", "Not funny.", "Irrelevant.", "Too technical."]

    for feedback in feedbacks:
        prompt_generator.generate_prompt(context, user_input, feedback)

    expected_feedback_list = feedbacks[-prompt_generator.max_feedbacks:]
    assert len(prompt_generator.feedback_list) == prompt_generator.max_feedbacks
    assert prompt_generator.feedback_list == expected_feedback_list


def test_clear_history(prompt_generator: PromptGenerator) -> None:
    """Test clearing the history of interactions and feedback."""
    prompt_generator.previous_interactions = ["Hello"]
    prompt_generator.feedback_list = ["Good response"]
    prompt_generator.clear_history()
    assert not prompt_generator.previous_interactions
    assert not prompt_generator.feedback_list


def test_incorporate_interaction(prompt_generator: PromptGenerator) -> None:
    """Test incorporating a single interaction."""
    interaction = "How do you do?"
    prompt_generator.incorporate_interaction(interaction)
    assert prompt_generator.previous_interactions[-1] == interaction


def test_incorporate_multiple_feedbacks(prompt_generator: PromptGenerator) -> None:
    """Test incorporating multiple feedbacks."""
    feedbacks = ["Too short.", "Not relevant."]
    prompt_generator.incorporate_feedback(feedbacks)
    assert prompt_generator.feedback_list == feedbacks
