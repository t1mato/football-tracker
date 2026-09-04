.PHONY: deps build test seed ci tz-check clean

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
#
# `build` rather than `seed` + `test`, because dbt test does not create
# relations: a test-only run errors on every schema test with "relation does
# not exist". build runs seeds, then models, then tests in DAG order.
#
# --warn-error-options is what makes CI more than an exit-code check: dbt
# build exits 0 on WARN, so a deprecation would pass unnoticed. Scoped to
# Deprecations on purpose -- the source accepted_values test is *designed* to
# warn on a couple of defective statuses, and blanket --warn-error would turn
# that routine signal into a red build. Verified both halves: the deprecated
# YAML shape errors under this flag, and the 2-row accepted_values warning
# still exits 0.
ci:
	cd transform && $(DBT) deps
	cd transform && $(DBT) run-operation create_empty_sources --target ci
	cd transform && $(DBT) build --target ci --warn-error-options '{"error": ["Deprecations"]}'
	$(MAKE) tz-check

# Runs the unit tests under a deliberately wrong session timezone. Any model
# that derives a date or hour from a timestamptz instead of the naive UTC
# form gives a different answer here than under `make test`, and fails.
#
# Unit tests only, for two reasons: assert_session_is_utc asserts the session
# IS UTC and so fails here by design, and the schema tests query views this
# database does not build.
tz-check:
	cd transform && $(DBT) run-operation create_empty_sources --target tz_probe
	cd transform && $(DBT) test --select test_type:unit --target tz_probe

# Removes transform/ci.duckdb too. dbt clean does not know about it, and a
# stale one is not harmless: create_empty_sources rebuilds from the
# declarations, but anything else left behind in that file persists.
clean:
	cd transform && $(DBT) clean
	rm -f transform/ci.duckdb
