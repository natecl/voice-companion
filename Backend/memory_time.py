"""Conservative calendar references from preserved evidence, never inferred expiry."""
from datetime import date, datetime, timedelta
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = 'calendar-reference-v1'


def resolve(expression, captured_at, timezone):
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
            return dict(result, reason='ambiguous_or_unsupported')
    except (ValueError, OverflowError):
        return dict(result, reason='invalid_date')
    # A calendar reference is not a validity interval or proof of event completion.
    return dict(result, resolution='calendar_date', date=day.isoformat(),
                reason='source_date_reference', anchor='source_capture')


def annotate(db, owner, claim):
    row = db.execute('''SELECT e.proposal,s.payload FROM memory_fact_evidence e
        JOIN source s ON s.owner=e.owner AND s.session=e.session AND s.revision=e.revision
        WHERE e.owner=? AND e.claim=? AND s.deleted=0
        AND EXISTS(SELECT 1 FROM support p WHERE p.claim=e.claim AND p.owner=e.owner
                   AND p.session=e.session AND p.revision=e.revision)''', (owner, claim['id'])).fetchone()
    if row is None:
        return
    proposal, source = json.loads(row['proposal']), json.loads(row['payload'])
    claim['temporal_evidence'] = dict(
        resolve(proposal['time']['expression'], source['captured_at'], source['timezone']),
        reported_status=proposal['time']['status'], basis=proposal['basis'],
        session=source['session_id'], revision=source['revision'])
