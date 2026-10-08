"""Rule set versioning, immutability enforcement, and change auditing."""

from __future__ import annotations

from typing import Any


class RuleSetImmutabilityError(ValueError):
    """Raised when an attempt is made to mutate an approved or retired rule set."""


def compare_rule_sets(
    current_manifest: dict[str, Any],
    target_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Compare two rule set manifests to audit changes before historical reclassification."""
    current_version = current_manifest.get("version", "unknown")
    target_version = target_manifest.get("version", "unknown")

    catalog_changed = (
        current_manifest.get("catalog_sha256") != target_manifest.get("catalog_sha256")
    )
    source_changed = (
        current_manifest.get("source_hash") != target_manifest.get("source_hash")
    )

    current_rules = set(current_manifest.get("rules", {}).keys())
    target_rules = set(target_manifest.get("rules", {}).keys())

    added_rules = sorted(target_rules - current_rules)
    removed_rules = sorted(current_rules - target_rules)
    common_rules = current_rules & target_rules

    modified_rules: list[str] = []
    for r in common_rules:
        if current_manifest.get("rules", {}).get(r) != target_manifest.get("rules", {}).get(r):
            modified_rules.append(r)
    modified_rules.sort()

    return {
        "current_version": current_version,
        "target_version": target_version,
        "catalog_changed": catalog_changed,
        "source_changed": source_changed,
        "added_rules": added_rules,
        "removed_rules": removed_rules,
        "modified_rules": modified_rules,
        "has_breaking_changes": bool(catalog_changed or removed_rules or modified_rules),
    }


def validate_rule_set_immutability(
    status: str,
    field_changed: str,
) -> None:
    """Ensure approved or retired rule sets cannot have their logic or catalog altered."""
    if status in {"approved", "retired"}:
        raise RuleSetImmutabilityError(
            f"Cannot modify '{field_changed}' on a rule set with status '{status}'. "
            "A new version must be created to alter approved classification rules."
        )
