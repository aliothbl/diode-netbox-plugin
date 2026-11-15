#!/usr/bin/env python
# Copyright 2026 NetBox Labs, Inc.
"""The apply transaction must also cover the active branch's connection."""
from contextlib import contextmanager
from unittest import mock

from django.test import SimpleTestCase

from netbox_diode_plugin.api import views
from netbox_diode_plugin.api.common import ChangeSetResult


class _FakeBranch:
    connection_name = "schema_branch_abc"


class ApplyBranchAtomicTestCase(SimpleTestCase):
    """_apply_one_changeset opens atomic() on the branch connection, outside the default one."""

    def _run(self, branch):
        entered = []

        @contextmanager
        def fake_atomic(using=None):
            entered.append(using)
            yield

        contextvar = mock.Mock()
        contextvar.get.return_value = branch
        with (
            mock.patch.object(views.transaction, "atomic", side_effect=fake_atomic),
            mock.patch.object(views, "Branch", object()),
            mock.patch("netbox_branching.contextvars.active_branch", contextvar),
            mock.patch.object(views, "apply_changeset", return_value=ChangeSetResult(id="cs")),
        ):
            result = views._apply_one_changeset(mock.Mock(id="cs"), mock.Mock())
        return entered, result

    def test_branch_connection_is_the_outer_transaction(self):
        """With a branch active, the branch connection's transaction is entered before the default one."""
        entered, result = self._run(_FakeBranch())
        self.assertEqual(entered, ["schema_branch_abc", None])
        self.assertEqual(result.id, "cs")

    def test_no_branch_only_default_transaction(self):
        """Without an active branch only the default connection's transaction is used."""
        entered, _ = self._run(None)
        self.assertEqual(entered, [None])
