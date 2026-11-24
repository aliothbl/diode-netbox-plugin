#!/usr/bin/env python
# Copyright 2026 NetBox Labs, Inc.
"""Diode NetBox Plugin - apply guards of /bulk-plan-apply/ (diode SPEC-20261124-1134)."""

from types import SimpleNamespace
from unittest import mock

from dcim.models import Site
from rest_framework import status
from utilities.testing import APITestCase

from netbox_diode_plugin.api import views as api_views
from netbox_diode_plugin.api.authentication import DiodeOAuth2Authentication
from netbox_diode_plugin.models import ObjectObservation
from netbox_diode_plugin.plugin_config import get_diode_user


class ApplyGuardTestCase(APITestCase):
    """An older observation must not overwrite a newer one; a stale plan is planned again."""

    url = "/netbox/api/plugins/diode/bulk-plan-apply/"

    def setUp(self):
        """Authenticate as the diode user and create the site under test."""
        self.auth = {"HTTP_AUTHORIZATION": "Bearer mocked_oauth_token"}
        diode_user = SimpleNamespace(
            user=get_diode_user(),
            token_scopes=["netbox:read", "netbox:write"],
            token_data={"scope": "netbox:read netbox:write"},
        )
        self.introspect = mock.patch.object(
            DiodeOAuth2Authentication, "_introspect_token", return_value=diode_user,
        )
        self.introspect.start()
        self.site = Site.objects.create(name="Guard Site", slug="guard-site", comments="c0", description="d0")

    def tearDown(self):
        """Stop the authentication patch."""
        self.introspect.stop()
        super().tearDown()

    def apply(self, site_fields, observed_at=None):
        entry = {
            "id": "e1",
            "object_type": "dcim.site",
            "entity": {"site": {"name": "Guard Site", "slug": "guard-site", **site_fields}},
        }
        if observed_at is not None:
            entry["observed_at"] = observed_at
        response = self.client.post(self.url, data={"entities": [entry]}, format="json", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        result = response.json()["results"][0]
        self.assertIsNone(result.get("errors"))
        self.site.refresh_from_db()
        return result

    # --- order: per-field observed_at ---

    def test_older_observation_does_not_overwrite_newer(self):
        """The newer observation is applied first; the older one arrives later and must not win."""
        self.apply({"comments": "newer"}, observed_at=2000)
        self.apply({"comments": "older"}, observed_at=1000)
        self.assertEqual(self.site.comments, "newer")
        obs = ObjectObservation.objects.get(object_type="dcim.site", object_id=self.site.pk)
        self.assertEqual(obs.fields["comments"], 2000)

    def test_newer_observation_overwrites_older(self):
        """Ordinary order still applies every observation."""
        self.apply({"comments": "first"}, observed_at=1000)
        self.apply({"comments": "second"}, observed_at=2000)
        self.assertEqual(self.site.comments, "second")

    def test_older_observation_still_writes_fields_nobody_newer_asserted(self):
        """The guard is per field: an older entity still writes a field only it asserted."""
        self.apply({"comments": "newer"}, observed_at=2000)
        self.apply({"comments": "older", "description": "only the older one says this"}, observed_at=1000)
        self.assertEqual(self.site.comments, "newer")
        self.assertEqual(self.site.description, "only the older one says this")

    def test_without_observed_at_last_apply_wins_as_before(self):
        """A reconciler that sends no observed_at gets the previous behaviour."""
        self.apply({"comments": "newer"}, observed_at=2000)
        self.apply({"comments": "no timestamp"})
        self.assertEqual(self.site.comments, "no timestamp")

    # --- stale plan: the row moved between plan and apply ---

    def _move_row_after_first_plan(self):
        """Patch the plan so that, right after the first one, another writer changes the site."""
        real = api_views.generate_changeset
        calls = {"n": 0}

        def plan_then_concurrent_write(entity, object_type):
            result = real(entity, object_type)
            calls["n"] += 1
            if calls["n"] == 1:
                site = Site.objects.get(pk=self.site.pk)
                site.description = "written by another batch"
                site.save()
            return result

        return mock.patch.object(api_views, "generate_changeset", side_effect=plan_then_concurrent_write), calls

    def test_stale_plan_is_planned_again(self):
        """
        Without the guard the UPDATE writes the merged state read at plan time and
        puts description back to "d0". With it, the apply sees the row moved, plans
        again, and both writes survive.
        """
        patcher, calls = self._move_row_after_first_plan()
        with patcher:
            self.apply({"comments": "from this entity"})
        self.assertEqual(calls["n"], 2)
        self.assertEqual(self.site.comments, "from this entity")
        self.assertEqual(self.site.description, "written by another batch")

    def test_row_that_keeps_moving_is_applied_after_the_last_replan(self):
        """A row that moves under every plan costs extra plans, never an error."""
        real = api_views.generate_changeset
        calls = {"n": 0}

        def always_moving(entity, object_type):
            result = real(entity, object_type)
            calls["n"] += 1
            site = Site.objects.get(pk=self.site.pk)
            site.description = f"move {calls['n']}"
            site.save()
            return result

        with mock.patch.object(api_views, "generate_changeset", side_effect=always_moving):
            self.apply({"comments": "eventually"})
        self.assertEqual(calls["n"], api_views.BulkPlanApplyView._MAX_REPLANS + 1)
        self.assertEqual(self.site.comments, "eventually")

    def test_manual_apply_change_set_is_not_guarded(self):
        """The guards belong to /bulk-plan-apply/ only: no observation rows elsewhere."""
        response = self.client.post(
            "/netbox/api/plugins/diode/apply-change-set/",
            data={"id": "cs1", "changes": [{
                "change_type": "update", "object_type": "dcim.site", "object_id": self.site.pk,
                "data": {"comments": "manual"},
            }]},
            format="json", **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.site.refresh_from_db()
        self.assertEqual(self.site.comments, "manual")
        self.assertFalse(ObjectObservation.objects.exists())
