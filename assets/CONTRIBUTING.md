# Contributing

Thanks for contributing to this repo! This guide will help you set up the development environment and provide tips on the code structure.

## Setting up the environment

### PostgreSQL and Redis

If you're using Docker:

1. Install Docker.
2. Run `docker compose build` at the root of this repository.
4. Start PostgreSQL and Redis with `docker compose up -d postgres-db redis-cache`. Note that this will not start the bot.

----

Without docker, check how to install and setup PostgreSQL and Redis-server on your OS.
Export the appropriate environment variables then you should be good to go.

### Installing the dependencies

1. Get Python 3.12 and pip
2. Install poetry with `pip install poetry`
3. Run `poetry install`
4. You may run commands inside the virtualenv with `poetry run ...`, or use `poetry env activate` to source the env

## Running the code

Before running any command, you must be in the poetry virtualenv, with the following environment variables exported:

```bash
poetry shell
export CARFIGURESBOT_DB_URL="postgres://ballsdex:defaultballsdexpassword@localhost:5432/ballsdex"
export CARFIGURESBOT_REDIS_URL="redis://127.0.0.1"
```

If needed, feel free to change the host, port, user or password of the database or redis server.

### Starting the bot

```bash
python3 -m carfigures --dev --debug
```

You can do `python3 -m ballsdex -h` to see the available options.
Replace `password` with the same value as the one in the `.env` file.
If appropriate, you may also replace `localhost` and `5432` for the host and the port.

### Starting the Admin Panel

**Warning: You need to run migrations from the bot at least once before starting the admin
panel without the other components.** You can either run the bot once or do `aerich upgrade`.

```bash
uvicorn ballsdex.core.admin:_app --host 0.0.0.0 --reload
```

## Migrations

When modifying the Tortoise models, create a migration file to reflect the changes using [aerich.](https://github.com/tortoise/aerich)

### Applying the changes from remote

When new migrations are available, you can either start the bot to run them automatically, or
execute the following command:

```sh
aerich upgrade
```

Once again, replace `password` with the same value as the one in the `.env` file.
If appropriate, you may also replace `localhost` and `5432` for the host and the port.

### Creating new migrations

If you modified the models, `aerich` can automatically generate a migration file.

**You need to make sure you have already ran previous migrations, and that your database
is not messy!** Aerich's behaviour can be odd if not in ideal conditions.

Execute the following command to generate migrations, and push the created files:

```sh
aerich migrate
```

## Coding style

The repo is validating and formatting code with `ruff` and statically checked by `pyright`.
They can be setup as a pre-commit hook to make them run before committing files:

```sh
pre-commit install
```

You can also run them manually:

```sh
pre-commit run -a
```
