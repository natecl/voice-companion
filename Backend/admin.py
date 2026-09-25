"""Run on the persistent service instance. Never prints credentials to logs."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from service_policy import open_ledger


def export_credential(store, url, destination, days):
    parsed = urlsplit(url)
    if (parsed.scheme != 'wss' or not parsed.hostname or parsed.path != '/stt'
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('Expected a public wss://host/stt URL')
    # Refuse to overwrite existing exports; no plaintext credential on stdout.
    with Path(destination).open('x') as output:
        os.chmod(destination, 0o600)
        identifier, token = store.enroll(lifetime_seconds=days * 86400)
        try:
            json.dump({'url': url, 'token': token}, output)
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            store.revoke(identifier)
            raise
    return identifier


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    enroll = commands.add_parser('enroll')
    enroll.add_argument('--url', required=True)
    enroll.add_argument('--output', required=True)
    enroll.add_argument('--days', type=int, choices=range(1, 31), default=7)
    revoke = commands.add_parser('revoke')
    revoke.add_argument('credential_id')
    commands.add_parser('usage')
    allowance = commands.add_parser('allow-one-recording', help='Requires explicit founder approval for this UTC day')
    allowance.add_argument('--date', required=True, help='Current UTC date, YYYY-MM-DD')
    allowance.add_argument('--replace-consumed', action='store_true', help='Separately approved replacement for an accidentally consumed extra attempt')
    grant = commands.add_parser('grant-recording-attempt', help='One separately founder-approved attempt; reuse its approval ID on retry')
    grant.add_argument('--date', required=True)
    grant.add_argument('--approval-id', required=True)
    args = parser.parse_args()
    store = open_ledger()
    try:
        if args.command == 'enroll':
            print('Enrolled credential ID:', export_credential(store, args.url, args.output, args.days))
        elif args.command == 'revoke':
            store.revoke(args.credential_id)
            print('Revocation recorded')
        elif args.command == 'grant-recording-attempt':
            day = datetime.strptime(args.date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            added = store.grant_recording_attempt(int(day.timestamp()), args.approval_id)
            print('Recording grant added' if added else 'Recording grant already exists')
        elif args.command == 'allow-one-recording':
            day = datetime.strptime(args.date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            store.allow_one_recording_today(int(day.timestamp()), replace_consumed=args.replace_consumed)
            print('One additional recording attempt authorized for UTC date', args.date)
        else:
            print(json.dumps({'reservations': store.usage()}))
    finally:
        store.close()


if __name__ == '__main__':
    main()
