"""Owner/revision-scoped note candidates; summaries are discovery, not source truth."""
import json
import re
from admission import Rejected
from memory_search import STOP_WORDS


def index(db, owner, session, revision, generation, notes):
    db.execute('DELETE FROM recording_note_index WHERE owner=? AND session=?', (owner, session))
    entries = [('Overview', notes['overview'])]
    entries += [(section['heading'], item) for section in notes['sections'] for item in section['items']]
    db.executemany('INSERT INTO recording_note_index VALUES(?,?,?,?,?,?,?)',
        [(owner, session, revision, generation, str(i),
          notes['title']+'\n'+heading+'\n'+item['text'], json.dumps(item['passages']))
         for i, (heading, item) in enumerate(entries)])


def migrate(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        db.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS recording_note_index USING fts5(
            owner UNINDEXED, session UNINDEXED, revision UNINDEXED,
            generation UNINDEXED, entry UNINDEXED, text, passages UNINDEXED,
            tokenize='unicode61')''')
        db.execute('DELETE FROM recording_note_index')
        for row in db.execute("""SELECT n.* FROM recording_notes n JOIN source s
            ON s.owner=n.owner AND s.session=n.session AND s.revision=n.revision
            WHERE n.state='ready' AND s.deleted=0""").fetchall():
            index(db, row['owner'], row['session'], row['revision'], row['generation_version'], json.loads(row['payload']))
        db.execute('PRAGMA user_version=18')
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise


def retrieve(store, owner, query, *, limit=6, exclude_session=None):
    if not isinstance(query, str) or len(query)>1000 or type(limit) is not int or not 1<=limit<=12:
        raise Rejected('invalid_query')
    terms = [t for t in dict.fromkeys(re.findall(r'\w+', query.casefold())) if t not in STOP_WORDS][:24]
    if not terms:
        return []
    from recording_notes import GENERATION_VERSION
    with store.connect() as db:
        rows = db.execute('''SELECT i.*,rank FROM recording_note_index i
            JOIN recording_notes n ON n.owner=i.owner AND n.session=i.session
              AND n.revision=i.revision AND n.generation_version=i.generation
            JOIN source s ON s.owner=i.owner AND s.session=i.session AND s.revision=i.revision
            WHERE recording_note_index MATCH ? AND i.owner=? AND n.state='ready'
              AND s.deleted=0 AND i.generation=? AND (? IS NULL OR i.session!=?)
            ORDER BY rank,i.session,i.entry LIMIT ?''',
            (' OR '.join('"'+t+'"' for t in terms), owner, GENERATION_VERSION, exclude_session, exclude_session, limit)).fetchall()
    return [dict(session_id=r['session'], revision=r['revision'], generation_version=r['generation'],
                 entry=r['entry'], text=r['text'], passages=json.loads(r['passages'])) for r in rows]
