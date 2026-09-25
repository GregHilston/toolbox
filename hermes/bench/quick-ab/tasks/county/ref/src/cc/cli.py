import click
from cc.stats import capacity_by_county
@click.group()
def main(): pass
@main.command()
@click.option("--min-stars", type=int, default=None)
def capacity(min_stars):
    click.echo("county,providers,capacity")
    for c, n, cap in capacity_by_county("data/providers.json", min_stars):
        click.echo(f"{c},{n},{cap}")
