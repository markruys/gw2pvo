default:
	cat Makefile

.PHONY: dist test

README.rst: README.md
	pandoc --from markdown --to rst --output=README.rst README.md

dist: README.rst
	python3 setup.py sdist bdist_wheel

