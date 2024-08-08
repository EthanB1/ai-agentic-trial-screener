# app/cli.py

import click
from flask.cli import with_appcontext
from .services.clinical_trials_gov_service import ClinicalTrialsGovService
from app.database import get_db
import logging
import asyncio

@click.command('populate-trials')
@click.option('--num-trials', default=1000, help='Number of trials to fetch (use 0 for all available)')
@click.option('--batch-size', default=100, help='Number of trials to fetch in each batch')
@with_appcontext
def populate_trials_command(num_trials, batch_size):
    """Fetch clinical trials from ClinicalTrials.gov and populate the database."""
    async def run():
        try:
            db = await get_db()
            new_trials, updated_trials = await ClinicalTrialsGovService.fetch_and_save_trials(num_trials=num_trials, batch_size=batch_size)
            click.echo(f'Successfully added {new_trials} new clinical trials and updated {updated_trials} existing trials in the database.')
        except Exception as e:
            logging.exception("An error occurred while populating trials")
            click.echo(f'An error occurred while populating trials: {str(e)}')
            click.echo("Check the logs for more details.")

    asyncio.run(run())

@click.command('db-stats')
@with_appcontext
def database_statistics_command():
    """Display statistics about the clinical trials database."""
    async def run():
        try:
            stats = await ClinicalTrialsGovService.get_database_statistics()
            
            click.echo("Clinical Trials Database Statistics:")
            click.echo(f"Total number of trials: {stats['total_trials']}")
            click.echo(f"Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
            
            click.echo("\nTrial Status Counts:")
            for status, count in stats['status_counts'].items():
                click.echo(f"  {status}: {count}")
            
            click.echo("\nTrial Phase Counts:")
            for phase, count in stats['phase_counts'].items():
                click.echo(f"  {phase}: {count}")
            
        except Exception as e:
            logger.error(f"An error occurred while fetching database statistics: {str(e)}")
            click.echo(f"An error occurred while fetching database statistics: {str(e)}")
            click.echo("Check the logs for more details.")

    asyncio.run(run())

def init_cli(app):
    app.cli.add_command(populate_trials_command)
    app.cli.add_command(database_statistics_command)