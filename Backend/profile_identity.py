"""Personal-source attribution contract; identity evidence stays separate from passage text."""
import hashlib
import re
from admission import Rejected

PROFILE_RUBRIC = 'personal-v1'
PROFILE_FIELDS = {
    'subject_scope': {'type':'string', 'enum':['user','related','other','unknown']},
    'subject_relation': {'type':['string','null']},
}


def personal(source):
    return source.get('origin') == 'personal_text'


def validate_identity(candidate):
    scope, name, relation = (candidate.get(k) for k in ('subject_scope','subject_name','subject_relation'))
    if scope not in ('user','related','other','unknown'):
        raise Rejected('invalid_profile_identity')
    if scope == 'user' and (name != 'user' or relation is not None):
        raise Rejected('invalid_profile_identity')
    if scope == 'related' and (not name or not isinstance(relation, str) or not 1 <= len(relation.strip()) <= 100):
        raise Rejected('invalid_profile_identity')
    if scope == 'unknown' and (name is not None or relation is not None):
        raise Rejected('invalid_profile_identity')
    if scope == 'other' and relation is not None:
        raise Rejected('invalid_profile_identity')


def profile_subject(source, candidate):
    if not personal(source):
        return None
    if candidate['subject_scope'] == 'user':
        return 'user'
    if candidate['subject_scope'] == 'related':
        # Only direct user identity is cross-session verified in this slice.
        # Preserve related subjects locally without name-based identity merges.
        identity = '|'.join((source['session_id'], candidate['subject_relation'].strip().casefold(), candidate['subject_name'].strip().casefold()))
        return 'related_' + hashlib.sha256(identity.encode()).hexdigest()[:24]
    return None


def identity_rule(source):
    if personal(source):
        return ('Application provenance establishes that the personal note author is the app user. '
                'Unquoted first-person statements can concern the user. Authorship does not identify quoted speakers '
                'or make other people\'s facts about the user. Preserve the subject and explicit relationships.')
    return ('First-person I/we and numbered speakers do not identify the app user or device owner. '
            'A claim about the user is unsupported unless that identity is explicitly established in the transcript. '
            'A claim about an unidentified speaker can preserve first-person evidence.')


def rank_related(candidate, pool):
    # Preserve older correction targets when recent unrelated profile facts fill the pool.
    ignored = {'the','user','now','instead','of','my','a','an','and','is','to','i'}
    terms = set(re.findall(r'\w+', candidate['text'].casefold())) - ignored
    return sorted(pool, key=lambda old: len(terms & (set(re.findall(r'\w+', old['text'].casefold())) - ignored)), reverse=True)[:4]
