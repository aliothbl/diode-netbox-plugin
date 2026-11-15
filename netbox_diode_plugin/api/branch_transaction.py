#!/usr/bin/env python
# Copyright 2026 NetBox Labs, Inc.
"""Transactions on the active netbox-branching branch's database connection."""

from contextlib import nullcontext

from django.apps import apps
from django.db import transaction


def active_branch_atomic():
    """
    transaction.atomic() on the active netbox-branching branch's connection, or a no-op.

    With a branch active, objects are written through the branch schema's own database
    connection, while transaction.atomic() alone only covers the default connection (where
    netbox-branching keeps ChangeDiff). Every transaction or savepoint the apply relies on must
    therefore be opened on both: outermost, it makes an apply atomic in the branch; nested, it is
    the savepoint that lets a caught IntegrityError leave the branch transaction usable.
    """
    if not apps.is_installed("netbox_branching"):
        return nullcontext()
    try:
        from netbox_branching.contextvars import active_branch
    except ImportError:
        return nullcontext()
    branch = active_branch.get()
    if branch is None:
        return nullcontext()
    return transaction.atomic(using=branch.connection_name)
