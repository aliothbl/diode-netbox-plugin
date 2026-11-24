#!/usr/bin/env python
# Copyright 2025 NetBox Labs, Inc.
"""
Guards for the auto-apply path (/bulk-plan-apply/) against lost updates.

The reconciler applies batches concurrently. Two things could make an older
state win over a newer one (diode SPEC-20261124-1134):

1. A stale plan. An UPDATE writes the merged state: the object as the plan
   read it plus what the entity asserted. If another batch wrote the object
   between this entity's plan and its apply, the UPDATE writes the old values
   of fields it never meant to change. Guard: the plan records the object's
   ``last_updated``; the apply locks the row and raises ``StalePlan`` when it
   moved, and the caller plans again against the current row.

2. Order. Two versions of one object (different entities, different
   ingestion logs) can be applied in any order. Guard: the reconciler sends
   each entity's ``observed_at``; ObjectObservation keeps, per object and
   field, the newest ``observed_at`` applied. Under the row lock, a field the
   entity asserted that already holds a newer observation is not written.

Both are active only inside ``apply_guard()``, which BulkPlanApplyView sets
per entity. Every other caller of the applier (manual /apply-change-set/,
/bulk-apply/) behaves as before.
"""

import contextvars
import logging
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Guard:
    observed_at: int | None
    branch: str
    enforce_fresh_plan: bool


_guard = contextvars.ContextVar("diode_apply_guard", default=None)


class StalePlan(Exception):
    """The row changed between this entity's plan and its apply."""

    def __init__(self, object_type: str, object_id: int):
        """Name the row that moved."""
        super().__init__(f"{object_type} {object_id} changed since it was planned")
        self.object_type = object_type
        self.object_id = object_id


@contextmanager
def apply_guard(observed_at: int | None, branch: str | None, enforce_fresh_plan: bool = True):
    """Activate the guards for the applies made inside this block."""
    token = _guard.set(_Guard(observed_at, branch or "", enforce_fresh_plan))
    try:
        yield
    finally:
        _guard.reset(token)


def parse_observed_at(value) -> int | None:
    """observed_at as sent by the reconciler: epoch milliseconds, or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value) or None
    return None


def get_for_update(model_class, change):
    """
    The row an UPDATE addressed by object_id writes to.

    Without a guard: a plain get, as before. With one: the row is locked until
    the apply commits (so concurrent applies of the same object take turns),
    and a row that moved since the plan raises StalePlan.
    """
    g = _guard.get()
    if g is None:
        return model_class.objects.get(id=change.object_id)
    instance = model_class.objects.select_for_update().get(id=change.object_id)
    planned = change.planned_last_updated
    if g.enforce_fresh_plan and planned is not None:
        current = getattr(instance, "last_updated", None)
        if current is not None and current != planned:
            raise StalePlan(change.object_type, change.object_id)
    return instance


def _locked_observation(g: _Guard, object_type: str, object_id: int):
    from netbox_diode_plugin.models import ObjectObservation

    obs, _ = ObjectObservation.objects.select_for_update().get_or_create(
        branch=g.branch, object_type=object_type, object_id=object_id,
    )
    return obs


def drop_superseded_fields(change, data: dict):
    """
    Remove from ``data`` the asserted fields a newer observation already wrote.

    Returns (data, observation, dropped). ``observation`` is the locked
    ObjectObservation row to pass to record_observation, or None when the
    order guard does not apply (no guard, no observed_at, nothing asserted).
    """
    g = _guard.get()
    if g is None or g.observed_at is None or not change.asserted or change.object_id is None:
        return data, None, []
    obs = _locked_observation(g, change.object_type, change.object_id)
    dropped = sorted(
        f for f in change.asserted
        if f in data and obs.fields.get(f, -1) > g.observed_at
    )
    for f in dropped:
        data.pop(f)
    if dropped:
        logger.info(
            "diode apply: %s %s keeps newer observed fields %s (entity observed_at=%s)",
            change.object_type, change.object_id, dropped, g.observed_at,
        )
    return data, obs, dropped


def still_writes(change, data: dict, dropped: list) -> bool:
    """
    False when dropping superseded fields left nothing the entity asserted.

    The fields that remain were merged in by the plan from the row as it was
    read, and the fresh-plan check has just confirmed the row did not move, so
    writing them would only rewrite current values.
    """
    if not dropped:
        return True
    return any(f in data for f in (change.asserted or ()))


def record_observation(change, object_id: int | None, obs=None):
    """Raise the stored observed_at of every field this entity asserted."""
    g = _guard.get()
    if g is None or g.observed_at is None or not change.asserted or object_id is None:
        return
    if obs is None:
        obs = _locked_observation(g, change.object_type, object_id)
    changed = False
    for f in change.asserted:
        if obs.fields.get(f, -1) < g.observed_at:
            obs.fields[f] = g.observed_at
            changed = True
    if changed:
        obs.save(update_fields=["fields"])
