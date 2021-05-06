# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue with owner or other contributers.

## Install Project Dependencies

* This project uses [**TA-Lib**](https://github.com/mrjbq7/ta-lib). Please visit the hyperlink for the official guide of installation.

## Create Dependency Requirements

1. Install [**pip-chill**](https://pypi.org/project/pip-chill/) by running `pip install pip-chill` which is a developer friendly version of classic `pip freeze`.
2. Update the `requirements.txt` file by running `pip-chill --all --no-version -v > requirements.txt`.
3. Ensure to **uncomment** all the dependency modules from the `requirements.txt`

## Pull Request Process

1. Ensure that dependecy list have been generated in the `requirements.txt` using above section.
2. If you are contributing new feature or a bug-fix, Always create a Pull Request to `new-features` branch as it have workflows to test the source before merging with the `main`.