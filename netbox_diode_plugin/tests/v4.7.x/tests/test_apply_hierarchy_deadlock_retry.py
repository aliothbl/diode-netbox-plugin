#!/usr/bin/env python
# Copyright 2026 NetBox Labs, Inc.
"""Retry of the ltree hierarchy deadlock NetBox reports as a ValidationError."""
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from netbox_diode_plugin.api import views
from netbox_diode_plugin.api.common import ChangeSetResult

HIERARCHY_DEADLOCK = "The hierarchy was modified concurrently; please retry."


def _hierarchy_deadlock():
    return ValidationError(HIERARCHY_DEADLOCK)


class IsHierarchyDeadlockTestCase(SimpleTestCase):
    """Detection of the ltree hierarchy deadlock ValidationError."""

    def test_matches_ltree_message(self):
        """The untranslated ltree message is recognised."""
        self.assertTrue(views._is_hierarchy_deadlock(_hierarchy_deadlock()))

    def test_matches_translated_message(self):
        """The message is recognised under a non-English locale."""
        with override_settings(LANGUAGE_CODE="pt"):
            from django.utils import translation
            with translation.override("pt"):
                from django.utils.translation import gettext_lazy
                exc = ValidationError(gettext_lazy(HIERARCHY_DEADLOCK))
                self.assertTrue(views._is_hierarchy_deadlock(exc))

    def test_other_validation_error_is_not_retryable(self):
        """Other ValidationErrors are not treated as deadlocks."""
        self.assertFalse(views._is_hierarchy_deadlock(ValidationError("Name cannot contain tab characters.")))
        self.assertFalse(views._is_retryable_apply_error(ValidationError({"name": ["required"]})))

    def test_non_validation_error(self):
        """Only ValidationError instances qualify."""
        self.assertFalse(views._is_hierarchy_deadlock(RuntimeError(HIERARCHY_DEADLOCK)))


class ApplyRetryOnHierarchyDeadlockTestCase(SimpleTestCase):
    """_apply_one_changeset_with_retry on the hierarchy deadlock."""

    def setUp(self):
        """Two retries, no real sleep."""
        patcher = mock.patch.object(views, "get_plugin_config", return_value=2)
        patcher.start()
        self.addCleanup(patcher.stop)
        sleep = mock.patch.object(views.time, "sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def test_retries_then_succeeds(self):
        """A hierarchy deadlock is retried and the retry result returned."""
        ok = ChangeSetResult(id="cs-1")
        with mock.patch.object(views, "_apply_one_changeset", side_effect=[_hierarchy_deadlock(), ok]) as apply:
            result = views._apply_one_changeset_with_retry(mock.Mock(), mock.Mock(), "1")
        self.assertIs(result, ok)
        self.assertEqual(apply.call_count, 2)

    def test_gives_up_after_max_retries(self):
        """After max retries the ValidationError propagates."""
        with mock.patch.object(views, "_apply_one_changeset", side_effect=_hierarchy_deadlock()) as apply:
            with self.assertRaises(ValidationError):
                views._apply_one_changeset_with_retry(mock.Mock(), mock.Mock(), "1")
        self.assertEqual(apply.call_count, 3)

    def test_other_validation_error_is_not_retried(self):
        """Other ValidationErrors are raised on the first attempt."""
        with mock.patch.object(views, "_apply_one_changeset", side_effect=ValidationError("boom")) as apply:
            with self.assertRaises(ValidationError):
                views._apply_one_changeset_with_retry(mock.Mock(), mock.Mock(), "1")
        self.assertEqual(apply.call_count, 1)


class BulkPlanApplyEntityHierarchyDeadlockTestCase(SimpleTestCase):
    """After retries, the deadlock fails only its entity, not the whole batch (no 500)."""

    def _process(self, apply_side_effect):
        plan_result = mock.Mock()
        plan_result.change_set.changes = [mock.Mock()]
        plan_result.change_set.to_dict.return_value = {"id": "cs-1"}
        extracted = mock.Mock(entity_data={}, object_type="dcim.devicerole", error=None)
        view = views.BulkPlanApplyView()
        with (
            mock.patch.object(view, "_run_plan", return_value=(plan_result, None)),
            mock.patch.object(views, "_apply_one_changeset_with_retry", side_effect=apply_side_effect),
            mock.patch.object(views, "_extract_entity_data", return_value=extracted),
        ):
            return view._process_entity({"id": "7", "object_type": "dcim.devicerole", "entity": {}}, None, mock.Mock())

    def test_exhausted_hierarchy_deadlock_is_per_entity_error(self):
        """Exhausted retries yield a per-entity apply error."""
        result = self._process(_hierarchy_deadlock())
        self.assertEqual(result["errors"], {"apply": {"__all__": ["db_deadlock_after_retries"]}})
        self.assertEqual(result["change_set"], {"id": "cs-1"})

    def test_other_validation_error_still_propagates(self):
        """Other ValidationErrors keep propagating."""
        with self.assertRaises(ValidationError):
            self._process(ValidationError("boom"))
