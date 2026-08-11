"""Management command deleting the stored tokens that can no longer be honoured."""

from django.core.management.base import BaseCommand

from jwt_allauth.tokens.purge import (
    purge,
    purge_sessions,
    retentions,
    session_retention,
    unknown_purposes,
)


class Command(BaseCommand):
    help = (
        'Delete the tokens that are past the lifetime of the flow that issued them: the '
        'single-use ones (password reset and set links, the capabilities they are '
        'exchanged for, email confirmations, MFA challenges, setup secrets and failed '
        'attempts) and the whitelisted refresh tokens of sessions that expired without '
        'being logged out. Nothing that is still usable is removed, so it is safe to run '
        'on a schedule.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be deleted without deleting anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verb = 'would be deleted' if dry_run else 'deleted'

        removed = purge(dry_run=dry_run)
        for purpose in sorted(removed):
            self.stdout.write(f'{purpose}: {removed[purpose]} {verb} (older than {retentions()[purpose]}).')

        sessions = purge_sessions(dry_run=dry_run)
        if sessions:
            self.stdout.write(
                f'expired sessions: {sessions} {verb} (older than {session_retention()}).'
            )

        total = sum(removed.values()) + sessions
        self.stdout.write(self.style.SUCCESS(f'{total} expired row(s) {verb}.'))

        unmanaged = unknown_purposes()
        if unmanaged:
            listed = ', '.join(f'{purpose} ({count})' for purpose, count in sorted(unmanaged.items()))
            self.stdout.write(
                self.style.WARNING(
                    'Left untouched, no retention configured for them: '
                    f'{listed}. Declare one through JWT_ALLAUTH_TOKEN_RETENTION to have '
                    'them purged as well.'
                )
            )
