#!/bin/sh
# Every check this product has, in one command. CI runs it on each pull request, and branch
# protection requires it to pass. Add each validator, linter, link checker, accessibility checker
# and browser test here as the product gains them. Started by the Founding Agents `setup` skill;
# the product owns it from here, and setup never replaces it.
set -e
if [ -d tests ]; then
  python3 -m unittest discover -s tests
fi
