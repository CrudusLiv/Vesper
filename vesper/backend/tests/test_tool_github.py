import pytest
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from app.agent.tools.integrations import GitHubToolExecutor
from app.agent.models import ToolCall


@pytest.fixture(autouse=True)
def mock_github_token(monkeypatch):
    """Mock GITHUB_TOKEN for all tests"""
    monkeypatch.setenv('GITHUB_TOKEN', 'fake_token_for_testing')


def _create_mock_pr(number, title, state="open", author="author"):
    """Helper to create a mock PR with proper datetime objects"""
    mock_pr = Mock()
    mock_pr.number = number
    mock_pr.title = title
    mock_pr.state = state
    mock_pr.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    mock_pr.html_url = f"https://github.com/org/repo/pull/{number}"
    mock_pr.user.login = author
    mock_pr.draft = False
    return mock_pr


def _create_mock_issue(number, title, state="open", author="reporter", labels=None):
    """Helper to create a mock issue with proper datetime objects"""
    mock_issue = Mock()
    mock_issue.number = number
    mock_issue.title = title
    mock_issue.state = state
    mock_issue.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    mock_issue.html_url = f"https://github.com/org/repo/issues/{number}"
    mock_issue.user.login = author
    if labels:
        # Create label mocks with name attribute properly set
        label_mocks = []
        for label in labels:
            mock_label = Mock()
            mock_label.name = label
            label_mocks.append(mock_label)
        mock_issue.labels = label_mocks
    else:
        mock_issue.labels = []
    return mock_issue


class TestGitHubToolExecutor:
    """Tests for GitHub sync tool executor"""

    def test_executor_initialization(self):
        """Test that executor initializes without error"""
        executor = GitHubToolExecutor()
        assert executor is not None

    def test_pull_prs_success(self):
        """Test successful pull_prs operation"""
        executor = GitHubToolExecutor()

        # Mock GitHub API response
        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            mock_pr1 = _create_mock_pr(123, "Add feature")

            mock_repo.get_pulls.return_value = [mock_pr1]
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_prs("org/repo", state="open", limit=10)

            assert result["success"] is True
            assert result["error"] is None
            assert len(result["result"]) == 1
            assert result["result"][0]["number"] == 123
            assert result["result"][0]["title"] == "Add feature"

    def test_pull_issues_success(self):
        """Test successful pull_issues operation"""
        executor = GitHubToolExecutor()

        # Mock GitHub API response
        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            mock_issue = _create_mock_issue(456, "Bug: layout broken", labels=["bug", "urgent"])

            mock_repo.get_issues.return_value = [mock_issue]
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_issues("org/repo", labels="bug", limit=10)

            assert result["success"] is True
            assert result["error"] is None
            assert len(result["result"]) == 1
            assert result["result"][0]["number"] == 456
            assert result["result"][0]["title"] == "Bug: layout broken"
            assert "bug" in result["result"][0]["labels"]

    def test_pull_prs_with_limit(self):
        """Test pull_prs respects limit parameter"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            # Create multiple PRs
            mock_prs = [_create_mock_pr(100 + i, f"PR {i}") for i in range(5)]

            mock_repo.get_pulls.return_value = mock_prs
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_prs("org/repo", state="open", limit=3)

            assert result["success"] is True
            assert len(result["result"]) == 3

    def test_pull_issues_with_labels(self):
        """Test pull_issues filters by labels"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            mock_issue = _create_mock_issue(789, "Critical bug", labels=["critical", "bug"])

            mock_repo.get_issues.return_value = [mock_issue]
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_issues("org/repo", labels="critical", limit=10)

            assert result["success"] is True
            mock_repo.get_issues.assert_called_once()
            call_kwargs = mock_repo.get_issues.call_args[1]
            assert call_kwargs.get("labels") is not None

    def test_execute_pull_prs_action(self):
        """Test execute method dispatches to pull_prs"""
        executor = GitHubToolExecutor()
        tool_call = ToolCall(
            tool_name="github_sync",
            parameters={
                "action": "pull_prs",
                "owner_repo": "org/repo",
                "state": "open",
                "limit": 5
            }
        )

        with patch.object(executor, 'pull_prs') as mock_pull:
            mock_pull.return_value = {"success": True, "result": [], "error": None}
            result = executor.execute(tool_call)

            mock_pull.assert_called_once_with("org/repo", state="open", limit=5)
            assert result["success"] is True

    def test_execute_pull_issues_action(self):
        """Test execute method dispatches to pull_issues"""
        executor = GitHubToolExecutor()
        tool_call = ToolCall(
            tool_name="github_sync",
            parameters={
                "action": "pull_issues",
                "owner_repo": "org/repo",
                "labels": "bug",
                "limit": 10
            }
        )

        with patch.object(executor, 'pull_issues') as mock_pull:
            mock_pull.return_value = {"success": True, "result": [], "error": None}
            result = executor.execute(tool_call)

            mock_pull.assert_called_once_with("org/repo", labels="bug", limit=10)
            assert result["success"] is True

    def test_execute_unknown_action(self):
        """Test execute returns error for unknown action"""
        executor = GitHubToolExecutor()
        tool_call = ToolCall(
            tool_name="github_sync",
            parameters={
                "action": "unknown_action",
                "owner_repo": "org/repo"
            }
        )

        result = executor.execute(tool_call)

        assert result["success"] is False
        assert "Unknown action" in result["error"]

    def test_pull_prs_auth_error(self):
        """Test pull_prs handles authentication error"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_github.side_effect = Exception("Bad credentials")

            result = executor.pull_prs("org/repo", state="open", limit=10)

            assert result["success"] is False
            assert result["error"] is not None
            assert "Bad credentials" in result["error"]

    def test_pull_issues_auth_error(self):
        """Test pull_issues handles authentication error"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_github.side_effect = Exception("Bad credentials")

            result = executor.pull_issues("org/repo", labels="bug", limit=10)

            assert result["success"] is False
            assert result["error"] is not None

    def test_pull_prs_empty_results(self):
        """Test pull_prs with no PRs found"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            mock_repo.get_pulls.return_value = []
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_prs("org/repo", state="open", limit=10)

            assert result["success"] is True
            assert result["result"] == []
            assert result["error"] is None

    def test_pull_issues_empty_results(self):
        """Test pull_issues with no issues found"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            mock_repo.get_issues.return_value = []
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_issues("org/repo", labels="bug", limit=10)

            assert result["success"] is True
            assert result["result"] == []
            assert result["error"] is None

    def test_pull_prs_rate_limit_error(self):
        """Test pull_prs handles rate limit error"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_github.side_effect = Exception("API rate limit exceeded")

            result = executor.pull_prs("org/repo", state="open", limit=10)

            assert result["success"] is False
            assert "rate limit" in result["error"].lower() or "API rate limit" in result["error"]

    def test_pull_issues_rate_limit_error(self):
        """Test pull_issues handles rate limit error"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_github.side_effect = Exception("API rate limit exceeded")

            result = executor.pull_issues("org/repo", labels="bug", limit=10)

            assert result["success"] is False
            assert "rate limit" in result["error"].lower() or "API rate limit" in result["error"]

    def test_pull_prs_closed_state(self):
        """Test pull_prs with closed state"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            mock_pr = _create_mock_pr(999, "Closed PR", state="closed")

            mock_repo.get_pulls.return_value = [mock_pr]
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_prs("org/repo", state="closed", limit=10)

            assert result["success"] is True
            mock_repo.get_pulls.assert_called_once()
            call_kwargs = mock_repo.get_pulls.call_args[1]
            assert call_kwargs["state"] == "closed"

    def test_pull_issues_multiple_labels(self):
        """Test pull_issues with multiple labels"""
        executor = GitHubToolExecutor()

        with patch('app.agent.tools.integrations.Github') as mock_github:
            mock_repo = Mock()
            mock_issue = _create_mock_issue(555, "Multi-label issue", labels=["bug", "critical", "urgent"])

            mock_repo.get_issues.return_value = [mock_issue]
            mock_github.return_value.get_user.return_value.get_repo.return_value = mock_repo

            result = executor.pull_issues("org/repo", labels="bug,critical", limit=10)

            assert result["success"] is True
            assert len(result["result"][0]["labels"]) == 3
