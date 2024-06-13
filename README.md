# Assertical (assertical)

Assertical is a library for helping write (async) integration/unit tests for fastapi/postgres/other projects. It has been developed by the Battery Storage and Grid Integration Program (BSGIP) at the Australian National University (https://bsgip.com/) for use with a variety of our internal libraries/packages.

It's attempting to be lightweight and modular, if you're note using `pandas` then just don't import the pandas asserts.

## Installation (for use)

`pip install assertical[all]`

## Installation (for dev)

`pip install -e .[all]`

## Modular Components

| **module** | **requires** |
| ---------- | ------------ |
| `asserts/generator` | `None`+ |
| `asserts/pandas` | `assertical[pandas]` |
| `fake/generator` | `None`+ |
| `fake/sqlalchemy` | `assertical[postgres]` |
| `fixtures/fastapi` | `assertical[fastapi]` |
| `fixtures/postgres` | `assertical[postgres]` |

+ No requirements are mandatory but additional types will be supported if `assertical[pydantic]`, `assertical[postgres]`, `assertical[xml]` are installed

All other types just require just the base `pip install assertical`

## Editors


### vscode

The file `vscode/settings.json` is an example configuration for vscode. To use these setting copy this file to `.vscode/settings,json`

The main features of this settings file are:
    - Enabling flake8 and disabling pylint
    - Autoformat on save (using the black and isort formatters)

Settings that you may want to change:
- Set the python path to your python in your venv with `python.defaultInterpreterPath`.
- Enable mypy by setting `python.linting.mypyEnabled` to true in settings.json.


