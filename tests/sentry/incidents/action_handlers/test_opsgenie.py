from unittest.mock import patch

import responses
from freezegun import freeze_time

from sentry.incidents.action_handlers import OpsgenieActionHandler
from sentry.incidents.logic import update_incident_status
from sentry.incidents.models import AlertRuleTriggerAction, IncidentStatus, IncidentStatusMethod
from sentry.models import Integration, OrganizationIntegration
from sentry.testutils.cases import TestCase
from sentry.utils import json

from . import FireTest

METADATA = {
    "api_key": "1234-ABCD",
    "base_url": "https://api.opsgenie.com/",
    "domain_name": "test-app.app.opsgenie.com",
}


@freeze_time()
class OpsgenieActionHandlerTest(FireTest, TestCase):
    def setUp(self):
        self.og_team = {"id": "123-id", "team": "cool-team", "integration_key": "1234-5678"}
        self.integration = Integration.objects.create(
            provider="opsgenie", name="hello-world", external_id="hello-world", metadata=METADATA
        )
        self.integration.add_organization(self.organization, self.user)
        self.org_integration = OrganizationIntegration.objects.get(
            organization_id=self.organization.id, integration_id=self.integration.id
        )
        self.org_integration.config = {"team_table": [self.og_team]}
        self.org_integration.save()

        self.action = self.create_alert_rule_trigger_action(
            target_identifier=self.og_team["id"],
            type=AlertRuleTriggerAction.Type.OPSGENIE,
            target_type=AlertRuleTriggerAction.TargetType.SPECIFIC,
            integration=self.integration,
        )

    def test_build_incident_attachment(self):
        from sentry.integrations.opsgenie.utils import build_incident_attachment

        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)
        update_incident_status(
            incident, IncidentStatus.CRITICAL, status_method=IncidentStatusMethod.RULE_TRIGGERED
        )
        self.create_alert_rule_trigger_action(
            target_identifier=self.og_team["id"],
            type=AlertRuleTriggerAction.Type.OPSGENIE,
            target_type=AlertRuleTriggerAction.TargetType.SPECIFIC,
            integration=self.integration,
        )
        metric_value = 1000
        data = build_incident_attachment(
            incident=incident, new_status=IncidentStatus(incident.status), metric_value=metric_value
        )

        assert data["message"] == alert_rule.name
        assert data["alias"] == f"incident_{incident.organization_id}_{incident.identifier}"
        assert data["description"] == "1000 events in the last 10 minutes"
        assert data["priority"] == "P1"
        assert (
            data["details"]["URL"]
            == f"http://testserver/organizations/baz/alerts/rules/details/{alert_rule.id}/?alert={incident.identifier}"
        )

    @responses.activate
    def run_test(self, incident, method):
        from sentry.integrations.opsgenie.utils import build_incident_attachment

        responses.add(
            responses.POST,
            url="https://api.opsgenie.com/v2/alerts",
            json={},
            status=202,
        )
        handler = OpsgenieActionHandler(self.action, incident, self.project)
        metric_value = 1000
        with self.tasks():
            getattr(handler, method)(metric_value, IncidentStatus(incident.status))
        data = responses.calls[0].request.body

        assert json.loads(data) == build_incident_attachment(
            incident, IncidentStatus(incident.status), metric_value
        )

    def test_fire_metric_alert(self):
        self.run_fire_test()

    def test_fire_metric_alert_multiple_teams(self):
        team2 = {"id": "456-id", "team": "cooler-team", "integration_key": "1234-7890"}
        self.org_integration.config["team_table"].append(team2)
        self.org_integration.save()

        self.run_fire_test()

    def test_resolve_metric_alert(self):
        self.run_fire_test("resolve")

    @responses.activate
    def test_rule_snoozed(self):
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule, status=IncidentStatus.CLOSED.value)
        self.snooze_rule(alert_rule=alert_rule)

        responses.add(
            responses.POST,
            url="https://api.opsgenie.com/v2/alerts",
            json={},
            status=202,
        )
        handler = OpsgenieActionHandler(self.action, incident, self.project)
        metric_value = 1000
        with self.tasks():
            handler.fire(metric_value, IncidentStatus(incident.status))

        assert len(responses.calls) == 0

    @patch("sentry.integrations.opsgenie.utils.logger")
    def test_missing_integration(self, mock_logger):
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)

        self.integration.delete()

        handler = OpsgenieActionHandler(self.action, incident, self.project)
        metric_value = 1000
        with self.tasks():
            handler.fire(metric_value, IncidentStatus(incident.status))

        assert len(responses.calls) == 0
        assert (
            mock_logger.info.call_args.args[0]
            == "Opsgenie integration removed, but the rule is still active."
        )

    @patch("sentry.integrations.opsgenie.utils.logger")
    def test_missing_team(self, mock_logger):
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)

        self.org_integration.config = {"team_table": []}
        self.org_integration.save()

        handler = OpsgenieActionHandler(self.action, incident, self.project)
        metric_value = 1000
        with self.tasks():
            handler.fire(metric_value, IncidentStatus(incident.status))

        assert len(responses.calls) == 0
        assert (
            mock_logger.info.call_args.args[0]
            == "Opsgenie team removed, but the rule is still active."
        )