# Contributing

Contributions are more than welcome using the fork and pull request approach 🙂 (if you are not familiar with this approach, please visit [_GitHub Docs PRs_](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests) for an extended documentation about collaborating with pull request; also, looking at previous merged pull requests helps to get familiar with this).

## Ground Rules

- We use Black code formatting
- We use Pylint
- We document our code

## Contribute to the software

1. Work on your own fork of the main repo
1. In the main repo execute:
    1. **pip install -r dev-requirements.txt** (this installs the [_dev-requirements.txt_](https://github.com/cssr-tools/pycopm/blob/main/dev-requirements.txt))
    1. **black src/ tests/** (this formats the code)
    1. **pylint src/ tests/** (this analyses the code, and might rise issues that need to be fixed before the pull request)
    1. **mypy --ignore-missing-imports src/ tests/** (this is a static checker, and might rise issues that need to be fixed before the pull request)
    1. **pytest --cov=pycopm --cov-report term-missing tests/** (this runs locally the tests, and might rise issues that need to be fixed before the pull request)
    1. **pycopm -i examples/decks/HELLO_WORLD.DATA -c 5,5,1 -m all -o output** (this runs the hello world example, which succeeds if the file output/HELLO_WORLD_PYCOPM.EGRID is created)
    1. **pushd docs & make html** (this generates the documentation, and might rise issues that need to be fixed before the pull request; if the build succeeds and if the contribution changes the documentation, then copy all content from the docs/_build/html/ folder and replace the files in the [_docs_](https://github.com/cssr-tools/pycopm/tree/main/docs) folder)
    * Tip for Linux users: See the [_ci_pycopm_ubuntu.yml_](https://github.com/cssr-tools/pycopm/blob/main/.github/workflows/ci_pycopm_ubuntu.yml) script and the [_Actions_](https://github.com/cssr-tools/pycopm/actions) for installation of pycopm, OPM Flow (binary packages), and dependencies, as well as the execution of the seven previous steps in Ubuntu 24.04 using Python 3.11.
    * Tip for macOS users: See the [_ci_pycopm_macos_.yml_](https://github.com/daavid00/OPM-Flow_macOS/blob/main/.github/workflows/ci_pycopm_macos.yml) script and the [_OPM-Flow_macOS Actions_](https://github.com/cssr-tools/pycopm/actions) for installation of pycopm, OPM Flow (source build), and dependencies, as well as running the tests and the hello world example in macOS 26 using Python3.13. Note that if you do not add the directory containing the OPM Flow executable to your system's PATH environment variable (e.g., export PATH=$PATH:/Users/yourname/pycopm/build/opm-simulators/bin), then you can pass this in the execution of the tests and pycopm using the flags **-f/--flow** (see [_ci_pycopm_macos.yml_](https://github.com/daavid00/OPM-Flow_macOS/blob/main/.github/workflows/ci_pycopm_macos.yml#L76)).
1. Squash your commits into a single commit (see this [_nice tutorial_](https://gist.github.com/lpranam/4ae996b0a4bc37448dc80356efbca7fa) if you are not familiar with this)
1. Push your commit and make a pull request
1. The maintainers will review the pull request, and if the contribution is accepted, then it will be merge to the main repo 

## Report issues or problems

1. Issues or problems can be raised by creating a [_new issue_](https://github.com/cssr-tools/pycopm/issues) in the repository GitHub page (if you are not familiar with this approach, please visit [_GitHub Docs Issues_](https://docs.github.com/en/issues/tracking-your-work-with-issues)).
1. We will try to answer as soon as possible, but also any user is more than welcome to answer. 

## Seek support

1. The preferred approach to seek support is to raise an Issue as described in the previous lines.
1. We will try to answer as soon as possible, but also any user is more than welcome to answer.
- An alternative approach is to send an email to any of the [_mantainers_](https://github.com/cssr-tools/pycopm/blob/main/pyproject.toml).
