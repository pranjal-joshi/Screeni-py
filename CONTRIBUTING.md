# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue with owner or other contributers.

## 1. Keep your Fork up to date
* Before statrting development of any new feature, Always check if this repo is ahead in commits as compared to your fork.
* It is a good practice to always keep your fork up-to-date before starting development of features/fixes to avoid merge conflicts.
* Update your fork using following code snippet.
```
# Add a new remote repo called as screenipy_upstream
git remote add screenipy_upstream https://github.com/pranjal-joshi/Screeni-py.git

# Sync your fork before starting work
git fetch screenipy_upstream
git checkout <BRANCH_YOU_ARE_WORKING_ON>
git merge screenipy_upstream/<BRANCH_FROM_THIS_REPO_YOU_WANT_TO_MERGE_IN_YOUR_BRANCH>
```


## 2. Install Project Dependencies

* This project uses [**TA-Lib**](https://github.com/mrjbq7/ta-lib). Please visit the hyperlink for the official guide of installation.
* This Project requires Python 3.9 environment setup. [Click Here to Download](https://www.python.org/downloads/)
* Install python dependencies by running `pip install -r requirements.txt` in the root directory of this project.

## 3. Create Dependency Requirements

1. Install [**pip-chill**](https://pypi.org/project/pip-chill/) by running `pip install pip-chill` which is a developer friendly version of classic `pip freeze`.
2. Update the `requirements.txt` file by running `pip-chill --all --no-version -v > requirements.txt`.
3. Ensure to **uncomment** all the dependency modules from the `requirements.txt`

## 4. Testing Code Locally

1. Update the test-cases as per the new features from `test/screenipy_test.py` if required.
2. Run a test locally with `pytest -v` and ensure that all tests are passed.
3. In case of a failure, Rectify code or Consider opening an issue for further discussion.

## 5. Pull Request Process

1. Ensure that dependecy list have been generated in the `requirements.txt` using above section.
2. Ensure that all test-cases are passed locally.
1. If you are contributing new feature or a bug-fix, Always create a Pull Request to `new-features` branch as it have workflows to test the source before merging with the `main`.