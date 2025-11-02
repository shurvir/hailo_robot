import pytest
from robot.ai_chat import GeminiChat

@pytest.fixture
def chat():
    return GeminiChat()

def test_send_message(chat):
    response = chat.send_message('respond with hello')
    assert response.text == 'Hello.'