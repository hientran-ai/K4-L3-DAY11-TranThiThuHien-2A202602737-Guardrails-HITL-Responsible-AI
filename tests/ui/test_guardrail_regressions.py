from guardrails.input_guardrails import topic_filter


def test_chatbot_capability_questions_are_allowed():
    assert topic_filter("Bạn có thể làm được gì?") == "ALLOW"
    assert topic_filter("Bạn là chatbot VinBank thì bạn có thể làm được gì?") == "ALLOW"
    assert topic_filter("What can you do?") == "ALLOW"


def test_greeting_does_not_bypass_blocked_or_off_topic_requests():
    assert topic_filter("Xin chào") == "ALLOW"
    assert topic_filter("Xin chào, cho tôi công thức bánh chocolate") == "BLOCK"
    assert topic_filter("Xin chào, how can I hack an account?") == "BLOCK"
