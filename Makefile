default:
	cat Makefile

.PHONY: dist test

README.rst: README.md
	pandoc --from markdown --to rst --output=README.rst README.md

dist: README.rst
	python setup.py sdist

test:
	python -m gw2pvo \
		--gw-system-id 9a6415bf-cdcc-48af-b393-2b442fa89a7f \
		--pvo-api-key 9a566660afe10cca98f0d97f053942d2007a4782 --pvo-system-id 49734 \
		--csv Test\ DATE.csv \
		--log debug
