# Build and Deploy

## Build and test

```sh
make setup          # create venv, install Playwright browsers
make test           # pytest -q, must pass before commit
make lint           # ruff check + ruff format --check
```

## Deploy

1. `make test` and `make lint` are green.
2. Tag the release: `git tag vX.Y.Z`.
3. `make deploy ENV=prod`. The target runs migrations, then restarts workers one at a time.
4. Watch `make logs ENV=prod` for five minutes. Roll back with `make rollback ENV=prod` if the error rate rises.
