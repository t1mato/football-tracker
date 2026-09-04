.PHONY: deps build test seed ci clean

DBT := $(CURDIR)/.venv/bin/dbt

deps:
	cd transform && $(DBT) deps

build:
	cd transform && $(DBT) build

test:
	cd transform && $(DBT) test

seed:
	cd transform && $(DBT) seed

# The order here is mandatory, not stylistic. dbt unit tests introspect the
# source relation for column types, so they fail with a confusing "relation
# doesn't exist" if create_empty_sources has not run first.
ci:
	cd transform && $(DBT) deps
	cd transform && $(DBT) run-operation create_empty_sources --target ci
	cd transform && $(DBT) seed --target ci
	cd transform && $(DBT) test --target ci

clean:
	cd transform && $(DBT) clean
