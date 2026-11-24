#!/usr/bin/env python
# Copyright 2025 NetBox Labs, Inc.
"""Diode NetBox Plugin - Database migrations."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Per-field newest observation of objects written by /bulk-plan-apply/."""

    dependencies = [
        ("netbox_diode_plugin", "0008_setting_branch"),
    ]

    operations = [
        migrations.CreateModel(
            name="ObjectObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch", models.CharField(blank=True, default="", max_length=100)),
                ("object_type", models.CharField(max_length=100)),
                ("object_id", models.BigIntegerField()),
                ("fields", models.JSONField(default=dict)),
            ],
            options={
                "default_permissions": (),
            },
        ),
        migrations.AddConstraint(
            model_name="objectobservation",
            constraint=models.UniqueConstraint(
                fields=("branch", "object_type", "object_id"),
                name="netbox_diode_plugin_objectobservation_unique",
            ),
        ),
    ]
