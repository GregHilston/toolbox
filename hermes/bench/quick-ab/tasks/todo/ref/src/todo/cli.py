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
    item = {"id": max((i["id"] for i in items), default=0) + 1, "text": text, "done": False}
    items.append(item)
    store.save(path, items)
    click.echo(f"added {item['id']}")


@main.command()
@click.argument("item_id", type=int)
@click.pass_obj
def done(path, item_id):
    items = store.load(path)
    for item in items:
        if item["id"] == item_id:
            item["done"] = True
            store.save(path, items)
            click.echo(f"done {item_id}")
            return
    click.echo(f"no item {item_id}")
    raise SystemExit(1)


@main.command(name="list")
@click.option("--pending", is_flag=True)
@click.pass_obj
def list_(path, pending):
    for item in store.load(path):
        if pending and item["done"]:
            continue
        mark = "x" if item["done"] else " "
        click.echo(f"[{mark}] {item['id']} {item['text']}")
