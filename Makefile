default:
	cat Makefile

.PHONY: dist test

README.rst: README.md
	pandoc --from markdown --to rst --output=README.rst README.md

dist: README.rst
	rm -fr dist
	python3 setup.py sdist bdist_wheel

pypi:
	python -m twine upload --repository gw2pvo dist/*

