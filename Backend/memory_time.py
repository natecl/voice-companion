"""Conservative calendar references from preserved evidence, never inferred expiry."""
from datetime import date, datetime, timedelta
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = 'calendar-reference-v2'
WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')


def resolve(expression, captured_at, timezone, *, reported_status=None):
    result = dict(version=VERSION, expression=expression, captured_at=captured_at,
                  timezone=timezone, resolution='unresolved', date=None)
    if expression is None:
        return dict(result, reason='no_expression')
    try:
        zone = ZoneInfo(timezone)
        anchor = datetime.fromtimestamp(captured_at, zone).date()
    except (ZoneInfoNotFoundError, ValueError, OverflowError, OSError):
        return dict(result, reason='invalid_anchor')
    text = expression.strip().casefold()
    # Whole-expression matching prevents silently discarding a qualifier or range.
    offsets = {'yesterday': -1, 'today': 0, 'tomorrow': 1}
    try:
        if text in offsets:
            day = anchor + timedelta(days=offsets[text])
        elif re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
            day = date.fromisoformat(text)
        else:
            day, reason = weekday_date(text, anchor)
            if day is None:
                return dict(result, reason=reason)
            if ((reported_status == 'future' and day < anchor)
                    or (reported_status == 'past' and day > anchor)):
                return dict(result, reason='conflicting_temporal_context')
    except (ValueError, OverflowError):
        return dict(result, reason='invalid_date')
    # A calendar reference is not a validity interval or proof of event completion.
    return dict(result, resolution='calendar_date', date=day.isoformat(),
                reason='source_date_reference', anchor='source_capture')


def weekday_date(text, anchor):
    """Only explicit week/direction wording; bare weekdays have no implied week."""
    names = '|'.join(WEEKDAYS)
    week = re.fullmatch(rf'({names}) (?:of )?(this|next|last) week', text)
    if week:
        name, period = week.groups()
        monday = anchor - timedelta(days=anchor.weekday())
        return monday + timedelta(days=7 * {'last': -1, 'this': 0, 'next': 1}[period]
                                  + WEEKDAYS.index(name)), None
    direction = re.fullmatch(rf'(this coming|upcoming|this past) ({names})', text)
    if direction:
        qualifier, name = direction.groups()
        distance = (WEEKDAYS.index(name) - anchor.weekday()) % 7
        # On the named day, words alone cannot distinguish today from a week away.
        if distance == 0:
            return None, 'same_day_ambiguity'
        return anchor + timedelta(days=distance if qualifier != 'this past' else distance - 7), None
    return None, 'ambiguous_or_unsupported'


def annotate(db, owner, claim):
    row = db.execute('''SELECT e.proposal,e.session FROM memory_fact_evidence e
        JOIN source s ON s.owner=e.owner AND s.session=e.session AND s.revision=e.revision
        WHERE e.owner=? AND e.claim=? AND (s.deleted=0 OR EXISTS(SELECT 1 FROM retained_recording r WHERE r.owner=e.owner AND r.session=e.session AND r.revision=e.revision))
        AND EXISTS(SELECT 1 FROM support p WHERE p.claim=e.claim AND p.owner=e.owner
                   AND p.session=e.session AND p.revision=e.revision)''', (owner, claim['id'])).fetchone()
    if row is None:
        return
    from memory_retention import source_metadata
    proposal, source = json.loads(row['proposal']), source_metadata(db,owner,row['session'])
    claim['temporal_evidence'] = dict(
        resolve(proposal['time']['expression'], source['captured_at'], source['timezone'],
                reported_status=proposal['time']['status']),
        reported_status=proposal['time']['status'], basis=proposal['basis'],
        session=source['session_id'], revision=source['revision'])
