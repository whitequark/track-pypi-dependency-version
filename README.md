track-pypi-dependency-version
=============================

The `track-pypi-dependency-version` script queries [PyPI][] for releases of a specified package and updates the upper bound for this package in a [requirements.txt style file][requirements.txt] such that it includes the newly arrived release.

For example, if `wasmtime` 5.0.0 is released and the requirements file contains `wasmtime>=1.0,<5`, it will be updated to contain `wasmtime>=1.0,<6`. While the script will respect more complex upper bounds like `<=4.0.1` when checking if a new release is within bounds, it will always replace the upper bound with `<MAJOR`.

[pypi]: https://pypi.org/
[requirements.txt]: https://pip.pypa.io/en/stable/reference/requirements-file-format/


Rationale
---------

Certain projects follow a release methodology where new major versions are released at a fast, regular cadence, with few changes to the interface, and the occasional breaking changes being of a kind that can be detected through automated testing. (E.g. [wasmtime-py][] releases new major versions every month, with the breaking changes causing an immediate crash.)

Having such a project as a dependency in the Python ecosystem causes issues. The two obvious approaches are:

1. Version constraint without upper bound (e.g. `wasmtime>=1.0`). As a result, when a breaking change is eventually released, everyone running `pip install my-package-using-wasmtime` will end up with a non-functinal install.
2. Version constraint with upper bound (e.g. `wasmtime>=1.0,<5`). As a result, without a prompt response to upstream releases, if multiple packages have the same dependency it is easy to end up with incompatible constraints, since Python only supports a single instance of a package globally.

Both of these approaches are frustrating to users and developers alike. In the second approach, once an upstream release happens, typically the downstream package will be released if it passes its testsuite. This script, together with your continuous integration system, automates these operations.

[wasmtime-py]: https://github.com/bytecodealliance/wasmtime-py


Using with GitHub Actions
-------------------------

This script is written for use with GitHub Actions, though it can be used with other CI systems just as well. The following workflow file can be used as inspiration:

```yaml
on:
  schedule:
    - cron: '0 0 * * *'
name: Track wasmtime releases
jobs:
  update_requirement:
    runs-on: ubuntu-latest
    steps:
      - name: Check out source code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.PUSH_TOKEN }}
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'
      - name: Check for a new release and update version requirement
        id: track-version
        run: |
          pip install git+https://github.com/whitequark/track-pypi-dependency-version.git
          track-pypi-dependency-version --status $GITHUB_OUTPUT -r dependencies.txt wasmtime
      - name: Test against updated version requirement
        if: steps.track-version.outputs.status == 'stale'
        run: |
          pip install .
          python -m unittest discover
      - name: Push updated version requirement
        if: steps.track-version.outputs.status == 'stale'
        uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: Update wasmtime version requirement from ${{ steps.track-version.outputs.old-requirement }} to ${{ steps.track-version.outputs.new-requirement }}.
```


LICENSE
-------

[0-clause BSD](LICENSE.txt)
