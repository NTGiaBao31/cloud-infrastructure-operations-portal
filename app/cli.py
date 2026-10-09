import click

from app.seed import SeedError, seed_demo_data
from app.services.alert_sync import sync_alerts


def register_cli(app):
    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Load or update the idempotent demo inventory."""
        try:
            summary = seed_demo_data()
        except SeedError as exc:
            click.echo(str(exc), err=True)
            raise SystemExit(1) from exc
        click.echo(
            "Demo data ready: "
            f"{summary['users']} users, {summary['servers']} servers, "
            f"{summary['alerts']} alerts, {summary['jobs']} jobs, {summary['audits']} audit rows."
        )

    @app.cli.command("sync-prometheus-alerts")
    def sync_prometheus_alerts_command():
        """Pull Prometheus alerts once. No background scheduler."""
        result = sync_alerts()
        click.echo(result.message)
        if not result.available:
            raise SystemExit(1)
