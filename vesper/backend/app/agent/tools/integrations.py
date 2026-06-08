"""Integration tools for external services like Google Calendar."""
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Any
from ..models import ToolCall

logger = logging.getLogger(__name__)

# Add .claude/scripts to path to import google_auth
PROJECT_DIR = Path(__file__).resolve().parents[5]
SCRIPTS_DIR = PROJECT_DIR / ".claude" / "scripts" / "integrations"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from google_auth import get_credentials
except ImportError:
    logger.warning("google_auth module not available in integrations")
    get_credentials = None

try:
    from googleapiclient.discovery import build
except ImportError:
    logger.warning("google-api-python-client not installed")
    build = None

try:
    from github import Github
except ImportError:
    logger.warning("PyGithub not installed")
    Github = None

import os


def _build_calendar_service():
    """Build and return Google Calendar service."""
    if not build:
        logger.error("google-api-python-client not installed")
        return None

    creds = get_credentials() if get_credentials else None
    if not creds:
        return None

    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"Failed to build calendar service: {e}")
        return None


class GCalToolExecutor:
    """Executes Google Calendar sync operations."""

    def execute(self, tool_call: ToolCall) -> dict:
        """Dispatch to specific action handler."""
        action = tool_call.parameters.get('action')

        if action == 'pull':
            limit = tool_call.parameters.get('limit', 10)
            days = tool_call.parameters.get('days', 14)
            return self.pull_events_from_gcal(limit=limit, days=days)
        elif action == 'push':
            data = tool_call.parameters.get('data', {})
            return self.push_schedule_to_gcal(data)
        else:
            return {
                "success": False,
                "result": None,
                "error": f"Unknown action: {action}. Use 'pull' or 'push'."
            }

    def pull_events_from_gcal(self, limit: int = 10, days: int = 14) -> dict:
        """
        Pull upcoming events from Google Calendar.

        Args:
            limit: Maximum number of events to retrieve
            days: Number of days to look ahead

        Returns:
            {"success": bool, "result": list[dict], "error": str | None}
        """
        if not get_credentials:
            return {
                "success": False,
                "result": None,
                "error": "Google credentials module not available"
            }

        creds = get_credentials()
        if not creds:
            return {
                "success": False,
                "result": None,
                "error": "Google credentials not configured. Ensure google_credentials.json exists."
            }

        service = _build_calendar_service()
        if not service:
            return {
                "success": False,
                "result": None,
                "error": "Failed to build Google Calendar service"
            }

        try:
            now = datetime.now(timezone.utc)
            later = now + timedelta(days=days)

            response = service.events().list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=later.isoformat(),
                maxResults=limit,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = []
            for item in response.get('items', []):
                start = item.get('start', {}).get('dateTime') or item.get('start', {}).get('date')
                end = item.get('end', {}).get('dateTime') or item.get('end', {}).get('date')

                events.append({
                    'id': item.get('id'),
                    'summary': item.get('summary', ''),
                    'start': start,
                    'end': end,
                    'location': item.get('location', ''),
                    'description': (item.get('description') or '')[:500],
                })

            return {
                "success": True,
                "result": events,
                "error": None
            }

        except Exception as e:
            logger.error(f"Failed to pull events from GCal: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": f"GCal API error: {str(e)}"
            }

    def push_schedule_to_gcal(self, event_data: dict) -> dict:
        """
        Push a schedule event to Google Calendar.

        Args:
            event_data: Dict with keys: title, date (YYYY-MM-DD), start_time (HH:MM),
                       end_time (HH:MM), location (optional), description (optional)

        Returns:
            {"success": bool, "result": {...}, "error": str | None}
        """
        if not get_credentials:
            return {
                "success": False,
                "result": None,
                "error": "Google credentials module not available"
            }

        creds = get_credentials()
        if not creds:
            return {
                "success": False,
                "result": None,
                "error": "Google credentials not configured. Ensure google_credentials.json exists."
            }

        service = _build_calendar_service()
        if not service:
            return {
                "success": False,
                "result": None,
                "error": "Failed to build Google Calendar service"
            }

        try:
            # Extract event details
            title = event_data.get('title', 'Event')
            date_str = event_data.get('date', '')
            start_time_str = event_data.get('start_time', '00:00')
            end_time_str = event_data.get('end_time', '01:00')
            location = event_data.get('location', '')
            description = event_data.get('description', '')

            # Construct ISO datetime strings
            start_dt = f"{date_str}T{start_time_str}:00"
            end_dt = f"{date_str}T{end_time_str}:00"

            # Build event object
            event = {
                'summary': title,
                'start': {
                    'dateTime': start_dt,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_dt,
                    'timeZone': 'UTC',
                }
            }

            if location:
                event['location'] = location
            if description:
                event['description'] = description

            # Check for duplicate events (conflict detection)
            # Query existing events with the same title on the same date
            self._check_for_duplicates(service, title, date_str)

            # Insert the event
            result = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            return {
                "success": True,
                "result": {
                    "gcal_event_id": result.get('id'),
                    "title": title,
                    "date": date_str,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"Failed to push event to GCal: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": f"GCal API error: {str(e)}"
            }

    def _check_for_duplicates(self, service: Any, title: str, date_str: str) -> Optional[list]:
        """
        Check if an event with the same title exists on the given date.

        Args:
            service: Google Calendar service object
            title: Event title
            date_str: Date string (YYYY-MM-DD)

        Returns:
            List of matching events or None
        """
        try:
            # Query events on that date with the same title
            date_obj = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            day_start = date_obj.isoformat()
            day_end = (date_obj + timedelta(days=1)).isoformat()

            response = service.events().list(
                calendarId='primary',
                timeMin=day_start,
                timeMax=day_end,
                q=title,  # Search by title
                singleEvents=True
            ).execute()

            matching = response.get('items', [])
            if matching:
                logger.info(f"Found {len(matching)} existing event(s) with title '{title}' on {date_str}")
            return matching

        except Exception as e:
            logger.warning(f"Could not check for duplicates: {e}")
            return None


class GitHubToolExecutor:
    """Executes GitHub repository monitoring operations."""

    def __init__(self):
        """Initialize GitHub client with token from environment."""
        self.token = os.getenv('GITHUB_TOKEN')
        if not self.token:
            logger.warning("GITHUB_TOKEN not set in environment")

    def execute(self, tool_call: ToolCall) -> dict:
        """Dispatch to specific action handler."""
        action = tool_call.parameters.get('action')

        if action == 'pull_prs':
            owner_repo = tool_call.parameters.get('owner_repo')
            state = tool_call.parameters.get('state', 'open')
            limit = tool_call.parameters.get('limit', 10)
            return self.pull_prs(owner_repo, state=state, limit=limit)
        elif action == 'pull_issues':
            owner_repo = tool_call.parameters.get('owner_repo')
            labels = tool_call.parameters.get('labels')
            limit = tool_call.parameters.get('limit', 10)
            return self.pull_issues(owner_repo, labels=labels, limit=limit)
        else:
            return {
                "success": False,
                "result": None,
                "error": f"Unknown action: {action}. Use 'pull_prs' or 'pull_issues'."
            }

    def pull_prs(self, owner_repo: str, state: str = 'open', limit: int = 10) -> dict:
        """
        Fetch pull requests from a GitHub repository.

        Args:
            owner_repo: Repository in format "owner/repo" (e.g., "anthropics/claude-code")
            state: PR state - "open", "closed", or "all" (default: "open")
            limit: Maximum number of PRs to retrieve (default: 10)

        Returns:
            {"success": bool, "result": list[dict], "error": str | None}
        """
        if not Github:
            return {
                "success": False,
                "result": None,
                "error": "PyGithub not installed"
            }

        if not self.token:
            return {
                "success": False,
                "result": None,
                "error": "GITHUB_TOKEN not configured. Set GITHUB_TOKEN environment variable."
            }

        try:
            g = Github(self.token)
            owner, repo = owner_repo.split('/')
            repository = g.get_user(owner).get_repo(repo)

            # Fetch PRs with specified state
            prs = repository.get_pulls(state=state)

            prs_list = []
            for i, pr in enumerate(prs):
                if i >= limit:
                    break

                prs_list.append({
                    'number': pr.number,
                    'title': pr.title,
                    'state': pr.state,
                    'created_at': pr.created_at.isoformat() if pr.created_at else None,
                    'url': pr.html_url,
                    'author': pr.user.login if pr.user else 'unknown',
                    'draft': pr.draft,
                })

            logger.info(f"Successfully fetched {len(prs_list)} PRs from {owner_repo}")
            return {
                "success": True,
                "result": prs_list,
                "error": None
            }

        except ValueError as e:
            logger.error(f"Invalid repository format: {owner_repo}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": f"Invalid repository format. Use 'owner/repo'. Error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to pull PRs from {owner_repo}: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": f"GitHub API error: {str(e)}"
            }

    def pull_issues(self, owner_repo: str, labels: Optional[str] = None, limit: int = 10) -> dict:
        """
        Fetch issues from a GitHub repository.

        Args:
            owner_repo: Repository in format "owner/repo" (e.g., "anthropics/claude-code")
            labels: Comma-separated labels to filter by (optional)
            limit: Maximum number of issues to retrieve (default: 10)

        Returns:
            {"success": bool, "result": list[dict], "error": str | None}
        """
        if not Github:
            return {
                "success": False,
                "result": None,
                "error": "PyGithub not installed"
            }

        if not self.token:
            return {
                "success": False,
                "result": None,
                "error": "GITHUB_TOKEN not configured. Set GITHUB_TOKEN environment variable."
            }

        try:
            g = Github(self.token)
            owner, repo = owner_repo.split('/')
            repository = g.get_user(owner).get_repo(repo)

            # Build query parameters
            kwargs = {'state': 'open'}
            if labels:
                kwargs['labels'] = [label.strip() for label in labels.split(',')]

            # Fetch issues
            issues = repository.get_issues(**kwargs)

            issues_list = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break

                issues_list.append({
                    'number': issue.number,
                    'title': issue.title,
                    'state': issue.state,
                    'created_at': issue.created_at.isoformat() if issue.created_at else None,
                    'url': issue.html_url,
                    'author': issue.user.login if issue.user else 'unknown',
                    'labels': [label.name for label in issue.labels] if issue.labels else [],
                })

            logger.info(f"Successfully fetched {len(issues_list)} issues from {owner_repo}")
            return {
                "success": True,
                "result": issues_list,
                "error": None
            }

        except ValueError as e:
            logger.error(f"Invalid repository format: {owner_repo}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": f"Invalid repository format. Use 'owner/repo'. Error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to pull issues from {owner_repo}: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": f"GitHub API error: {str(e)}"
            }
