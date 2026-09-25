from pathlib import Path

import click

from todo import store


@click.group()
@click.option("--file", "path", type=click.Path(path_type=Path), default=Path("todo.json"))
@click.pass_context
def main(ctx, path):
    ctx.obj = path


@main.command()
@click.argument("text")
@click.pass_obj
def add(path, text):
    items = store.load(path)
    item = {"id": len(items) + 1, "text": text, "done": False}
    items.append(item)
    store.save(path, items)
    click.echo(f"added {item['id']}")


@main.command(name="list")
@click.pass_obj
def list_(path):
    for item in store.load(path):
        mark = "x" if item["done"] else " "
        click.echo(f"[{mark}] {item['id']} {item['text']}")
