import pytest
from textual.app import App

from git_reverse.storage.database import Database
from git_reverse.tui.chat import ChatPane, ChatArea


@pytest.mark.asyncio
async def test_chat_pane_creation(db: Database) -> None:
    """Verify that ChatPane can be instantiated and composed within an app."""
    class TestApp(App[None]):
        def compose(self):
            yield ChatPane(db=db, api_key="mock_key", default_model="gpt-4o-mini")

    app = TestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(ChatPane)
        assert pane.session_id is None
        assert pane.repo_id is None
        assert app.query_one(ChatArea) is not None
