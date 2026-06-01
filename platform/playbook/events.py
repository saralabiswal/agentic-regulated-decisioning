# Author: Sarala Biswal
"""In-process Playbook event buffer for API streaming."""

from __future__ import annotations

from collections import defaultdict

from core.schemas import PlaybookLayerEvent, PlaybookRuleAppliedEvent

_EVENTS: dict[str, list[PlaybookRuleAppliedEvent]] = defaultdict(list)
_LAYER_EVENTS: dict[str, list[PlaybookLayerEvent]] = defaultdict(list)


def publish_rule_event(event: PlaybookRuleAppliedEvent) -> None:
    """Store one in-process Playbook rule event."""
    _EVENTS[event.submission_id].append(event)


def list_rule_events(submission_id: str) -> list[PlaybookRuleAppliedEvent]:
    """Return rule events recorded for a submission."""
    return list(_EVENTS.get(submission_id, []))


def publish_layer_event(event: PlaybookLayerEvent) -> None:
    """Store one in-process Playbook layer event."""
    _LAYER_EVENTS[event.submission_id].append(event)


def list_layer_events(submission_id: str) -> list[PlaybookLayerEvent]:
    """Return layer events recorded for a submission."""
    return list(_LAYER_EVENTS.get(submission_id, []))


def reset() -> None:
    """Clear in-process event or stream state for tests and demos."""
    _EVENTS.clear()
    _LAYER_EVENTS.clear()
