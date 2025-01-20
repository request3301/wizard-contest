import pytest


@pytest.fixture
def mock_groq_response(mocker):
    def _mock_response(content: str):
        mock = mocker.AsyncMock()
        mock.choices = [
            mocker.Mock(
                message=mocker.Mock(
                    content=content
                )
            )
        ]
        return mock

    return _mock_response
