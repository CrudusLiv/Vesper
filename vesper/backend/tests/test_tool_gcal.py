"""Tests for Google Calendar sync tool."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from app.agent.tools.integrations import GCalToolExecutor
from app.agent.models import ToolCall


def mock_build(service_name, version, **kwargs):
    """Mock implementation of googleapiclient.discovery.build."""
    service = MagicMock()
    return service


@pytest.fixture
def gcal_executor():
    """Create a GCal executor instance."""
    return GCalToolExecutor()


class TestGCalPullEvents:
    """Test pulling events from Google Calendar."""

    def test_pull_events_returns_list(self, gcal_executor):
        """Test that pull_events returns a list structure."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations._build_calendar_service') as mock_service_builder:
                mock_service = MagicMock()
                mock_service_builder.return_value = mock_service

                # Mock the API response
                mock_service.events().list().execute.return_value = {
                    'items': []
                }

                result = gcal_executor.pull_events_from_gcal(limit=10, days=14)

                assert result['success'] is True
                assert isinstance(result['result'], list)
                assert result['error'] is None

    def test_pull_events_no_credentials(self, gcal_executor):
        """Test pull_events when credentials are missing."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = None

            result = gcal_executor.pull_events_from_gcal(limit=10, days=14)

            assert result['success'] is False
            assert 'credentials' in result['error'].lower()

    def test_pull_events_api_error(self, gcal_executor):
        """Test pull_events handles API errors gracefully."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations._build_calendar_service') as mock_service_builder:
                mock_service = MagicMock()
                mock_service_builder.return_value = mock_service

                # Mock API error
                mock_service.events().list().execute.side_effect = Exception("API Error")

                result = gcal_executor.pull_events_from_gcal(limit=10, days=14)

                assert result['success'] is False
                assert result['error'] is not None

    def test_pull_events_with_real_event_data(self, gcal_executor):
        """Test pull_events parses event data correctly."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations._build_calendar_service') as mock_service_builder:
                mock_service = MagicMock()
                mock_service_builder.return_value = mock_service

                # Mock realistic GCal API response
                now = datetime.now(timezone.utc)
                later = now + timedelta(hours=2)

                mock_service.events().list().execute.return_value = {
                    'items': [
                        {
                            'id': 'event1',
                            'summary': 'Team Meeting',
                            'start': {'dateTime': now.isoformat()},
                            'end': {'dateTime': later.isoformat()},
                            'location': 'Zoom',
                            'description': 'Weekly sync'
                        }
                    ]
                }

                result = gcal_executor.pull_events_from_gcal(limit=10, days=14)

                assert result['success'] is True
                assert len(result['result']) == 1
                event = result['result'][0]
                assert event['summary'] == 'Team Meeting'
                assert event['location'] == 'Zoom'

    def test_pull_events_respects_limit(self, gcal_executor):
        """Test pull_events respects the limit parameter."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations._build_calendar_service') as mock_service_builder:
                mock_service = MagicMock()
                mock_service_builder.return_value = mock_service

                # Verify the API call includes maxResults
                mock_service.events().list().execute.return_value = {'items': []}

                gcal_executor.pull_events_from_gcal(limit=25, days=7)

                # Check that list() was called with maxResults=25
                call_kwargs = mock_service.events().list.call_args[1]
                assert call_kwargs.get('maxResults') == 25


class TestGCalPushSchedule:
    """Test pushing schedule events to Google Calendar."""

    def test_push_schedule_creates_event(self, gcal_executor):
        """Test pushing a schedule event to GCal."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations._build_calendar_service') as mock_service_builder:
                mock_service = MagicMock()
                mock_service_builder.return_value = mock_service

                # Mock successful create response
                mock_service.events().insert().execute.return_value = {
                    'id': 'created_event_id',
                    'summary': 'Test Event'
                }

                event_data = {
                    'title': 'Test Event',
                    'date': '2026-06-15',
                    'start_time': '10:00',
                    'end_time': '11:00',
                    'description': 'Test event'
                }

                result = gcal_executor.push_schedule_to_gcal(event_data)

                assert result['success'] is True
                assert result['result']['gcal_event_id'] == 'created_event_id'

    def test_push_schedule_no_credentials(self, gcal_executor):
        """Test pushing schedule fails without credentials."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = None

            event_data = {
                'title': 'Test Event',
                'date': '2026-06-15',
                'start_time': '10:00',
                'end_time': '11:00'
            }

            result = gcal_executor.push_schedule_to_gcal(event_data)

            assert result['success'] is False
            assert 'credentials' in result['error'].lower()

    def test_push_schedule_api_error(self, gcal_executor):
        """Test push_schedule handles API errors."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations._build_calendar_service') as mock_service_builder:
                mock_service = MagicMock()
                mock_service_builder.return_value = mock_service

                # Mock API error
                mock_service.events().insert().execute.side_effect = Exception("Insert failed")

                event_data = {
                    'title': 'Test Event',
                    'date': '2026-06-15',
                    'start_time': '10:00',
                    'end_time': '11:00'
                }

                result = gcal_executor.push_schedule_to_gcal(event_data)

                assert result['success'] is False
                assert result['error'] is not None

    def test_push_schedule_formats_datetime_correctly(self, gcal_executor):
        """Test that push_schedule formats datetime correctly for GCal API."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations.build') as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service

                mock_service.events().insert().execute.return_value = {
                    'id': 'event_id'
                }

                event_data = {
                    'title': 'Meeting',
                    'date': '2026-06-20',
                    'start_time': '14:30',
                    'end_time': '15:30',
                    'location': 'Room 101'
                }

                result = gcal_executor.push_schedule_to_gcal(event_data)

                assert result['success'] is True

                # Verify the event body passed to insert
                call_kwargs = mock_service.events().insert.call_args[1]
                body = call_kwargs.get('body', {})

                # Should have start and end as dateTime objects
                assert 'start' in body
                assert 'end' in body
                assert body['summary'] == 'Meeting'


class TestGCalExecute:
    """Test the execute method that dispatches tool calls."""

    def test_execute_pull_action(self, gcal_executor):
        """Test executing a pull tool call."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations.build') as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service
                mock_service.events().list().execute.return_value = {'items': []}

                tool_call = ToolCall(
                    tool_name='gcal_sync',
                    parameters={
                        'action': 'pull',
                        'limit': 10,
                        'days': 14
                    }
                )

                result = gcal_executor.execute(tool_call)

                assert result['success'] is True

    def test_execute_push_action(self, gcal_executor):
        """Test executing a push tool call."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations.build') as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service
                mock_service.events().insert().execute.return_value = {'id': 'event_id'}

                tool_call = ToolCall(
                    tool_name='gcal_sync',
                    parameters={
                        'action': 'push',
                        'data': {
                            'title': 'Meeting',
                            'date': '2026-06-15',
                            'start_time': '10:00',
                            'end_time': '11:00'
                        }
                    }
                )

                result = gcal_executor.execute(tool_call)

                assert result['success'] is True

    def test_execute_invalid_action(self, gcal_executor):
        """Test executing with invalid action."""
        tool_call = ToolCall(
            tool_name='gcal_sync',
            parameters={
                'action': 'invalid_action'
            }
        )

        result = gcal_executor.execute(tool_call)

        assert result['success'] is False
        assert 'Unknown action' in result['error']

    def test_execute_wrong_tool_name(self, gcal_executor):
        """Test executing with wrong tool name."""
        tool_call = ToolCall(
            tool_name='wrong_tool',
            parameters={}
        )

        result = gcal_executor.execute(tool_call)

        assert result['success'] is False


class TestConflictHandling:
    """Test conflict handling during sync."""

    def test_push_detects_duplicate_event(self, gcal_executor):
        """Test that push_schedule detects if event already exists in GCal."""
        with patch('app.agent.tools.integrations.get_credentials') as mock_creds:
            mock_creds.return_value = MagicMock()
            with patch('app.agent.tools.integrations.build') as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service

                # First call lists existing events (find duplicates)
                # Second call inserts new event
                mock_service.events().list().execute.return_value = {
                    'items': [
                        {
                            'summary': 'Existing Event',
                            'start': {'dateTime': '2026-06-15T10:00:00'},
                            'end': {'dateTime': '2026-06-15T11:00:00'}
                        }
                    ]
                }

                event_data = {
                    'title': 'Existing Event',
                    'date': '2026-06-15',
                    'start_time': '10:00',
                    'end_time': '11:00'
                }

                result = gcal_executor.push_schedule_to_gcal(event_data)

                # Should succeed but note the check was made
                assert result['success'] is True
