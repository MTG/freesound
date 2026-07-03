import re
from unittest.mock import Mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from prometheus_client import CollectorRegistry, generate_latest

import utils.management_commands as management_commands
import utils.prometheus_metrics as prometheus_metrics
from utils.management_commands import LoggingBaseCommand
from utils.prometheus_metrics import make_command_registry, push_to_gateway_safe


class MetricsEndpointTest:
    def test_metrics_endpoint_uses_current_token_setting(self, client, settings):
        # none token is 404
        settings.PROMETHEUS_METRICS_TOKEN = None
        assert client.get("/metrics").status_code == 404

        # empty token is 404
        settings.PROMETHEUS_METRICS_TOKEN = ""
        assert client.get("/metrics").status_code == 404

        # wrong token/correct token
        settings.PROMETHEUS_METRICS_TOKEN = "test-token"  # noqa: S105
        assert client.get("/metrics").status_code == 401
        assert client.get("/metrics", HTTP_AUTHORIZATION="Bearer wrong").status_code == 401

        response = client.get("/metrics", HTTP_AUTHORIZATION="Bearer test-token")

        assert response.status_code == 200
        assert b"python_info" in response.content

    def test_metrics_endpoint_requires_get(self, client, settings):
        # only supports GET
        settings.PROMETHEUS_METRICS_TOKEN = "test-token"  # noqa: S105

        response = client.post("/metrics")

        assert response.status_code == 405


class PushgatewayHelperTest:
    def test_push_to_gateway_safe_noops_without_url(self, monkeypatch, settings):
        settings.PROMETHEUS_PUSHGATEWAY_URL = None
        mocked_push_to_gateway = Mock()
        monkeypatch.setattr(prometheus_metrics, "push_to_gateway", mocked_push_to_gateway)
        registry = CollectorRegistry()

        push_to_gateway_safe("test-job", registry)

        mocked_push_to_gateway.assert_not_called()

    def test_push_to_gateway_safe_pushes_with_timeout(self, monkeypatch, settings):
        settings.PROMETHEUS_PUSHGATEWAY_URL = "http://pushgateway:9091"
        settings.PROMETHEUS_PUSHGATEWAY_TIMEOUT_SECONDS = 5
        mocked_push_to_gateway = Mock()
        monkeypatch.setattr(prometheus_metrics, "push_to_gateway", mocked_push_to_gateway)
        registry = CollectorRegistry()

        push_to_gateway_safe("test-job", registry)

        mocked_push_to_gateway.assert_called_once_with(
            "http://pushgateway:9091",
            job="test-job",
            registry=registry,
            timeout=5,
        )

    def test_push_to_gateway_safe_swallows_push_errors(self, monkeypatch, settings):
        settings.PROMETHEUS_PUSHGATEWAY_URL = "http://pushgateway:9091"
        mocked_push_to_gateway = Mock(side_effect=OSError("unreachable"))
        monkeypatch.setattr(prometheus_metrics, "push_to_gateway", mocked_push_to_gateway)
        registry = CollectorRegistry()

        push_to_gateway_safe("test-job", registry)

        mocked_push_to_gateway.assert_called_once()


class SuccessfulCommand(LoggingBaseCommand):
    def handle(self, *args, **options):
        return "done"


class FailingCommand(LoggingBaseCommand):
    def handle(self, *args, **options):
        raise CommandError("nope")


class SystemExitCommand(LoggingBaseCommand):
    def handle(self, *args, **options):
        raise SystemExit(0)


class LoggingBaseCommandMetricsTest:
    def test_successful_command_pushes_success_and_duration(self, monkeypatch):
        mocked_push_to_gateway_safe = Mock()
        monkeypatch.setattr(management_commands, "push_to_gateway_safe", mocked_push_to_gateway_safe)

        output = call_command(SuccessfulCommand())

        assert output == "done"
        mocked_push_to_gateway_safe.assert_called_once()
        assert mocked_push_to_gateway_safe.call_args.kwargs["job"] == "test_prometheus_metrics"
        metrics = generate_latest(mocked_push_to_gateway_safe.call_args.kwargs["registry"])
        assert b"freesound_management_command_last_success 1.0" in metrics
        assert re.search(rb"freesound_management_command_last_duration_seconds [0-9.]+", metrics)

    def test_failing_command_pushes_failure_and_reraises(self, monkeypatch):
        mocked_push_to_gateway_safe = Mock()
        monkeypatch.setattr(management_commands, "push_to_gateway_safe", mocked_push_to_gateway_safe)

        with pytest.raises(CommandError):
            call_command(FailingCommand())

        mocked_push_to_gateway_safe.assert_called_once()
        metrics = generate_latest(mocked_push_to_gateway_safe.call_args.kwargs["registry"])
        assert b"freesound_management_command_last_success 0.0" in metrics

    def test_clean_system_exit_counts_as_success(self, monkeypatch):
        mocked_push_to_gateway_safe = Mock()
        monkeypatch.setattr(management_commands, "push_to_gateway_safe", mocked_push_to_gateway_safe)

        with pytest.raises(SystemExit):
            call_command(SystemExitCommand())

        metrics = generate_latest(mocked_push_to_gateway_safe.call_args.kwargs["registry"])
        assert b"freesound_management_command_last_success 1.0" in metrics

    def test_make_command_registry_contains_only_command_metrics(self):
        registry = make_command_registry(duration_seconds=1.2, success=True)

        metrics = generate_latest(registry)

        assert b"freesound_management_command_last_duration_seconds 1.2" in metrics
        assert b"freesound_management_command_last_success 1.0" in metrics
        assert b"python_info" not in metrics
