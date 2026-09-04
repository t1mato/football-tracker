{#
  Creates empty tables for every declared source.

  dbt unit tests introspect the source relation to learn column types, so
  they cannot run at all when the relation is absent -- declaring data_type
  in YAML does NOT substitute, that was tried and fails identically. The
  relation must exist but may be empty, which is exactly what CI needs.

  Reading graph.sources makes _sources.yml the single source of truth: no
  parallel DDL file to drift, no CSV fixtures to hand-maintain, no binary
  database in git.

  DuckDB-only by design. The data_type values in _sources.yml are DuckDB
  spellings (bigint, varchar, timestamp with time zone) and are emitted into
  DDL verbatim. A BigQuery CI target would need its own type mapping; this
  macro is the local/CI bootstrap, not part of the warehouse swap.
#}
{% macro create_empty_sources() %}

  {#
    Refuses to run anywhere but the disposable targets. Without this guard a
    bare `dbt run-operation create_empty_sources` defaults to dev and would
    replace raw.* in the real warehouse -- 7,655 matches, four seasons of
    backfill that the API's rolling window means we could not re-fetch.
  #}
  {% if target.name not in ['ci', 'tz_probe'] %}
    {% do exceptions.raise_compiler_error(
      "create_empty_sources refuses to run against target '" ~ target.name ~
      "'. It replaces the raw.* tables, which on dev would destroy the "
      "backfilled warehouse. Use --target ci or --target tz_probe.") %}
  {% endif %}

  {% for node in graph.sources.values() %}
    {% set cols = node.columns.values() | list %}

    {#
      A source declared without columns would be skipped silently here, and
      the unit tests would then fail with the confusing "relation doesn't
      exist" that this macro exists to prevent. Fail loudly at the source.
    #}
    {% if not cols %}
      {% do exceptions.raise_compiler_error(
        "source " ~ node.schema ~ "." ~ node.identifier ~ " declares no "
        "columns, so no empty relation can be built for it and any unit test "
        "touching it will fail with 'relation doesn't exist'. Add a columns: "
        "block to _sources.yml.") %}
    {% endif %}

    {% do run_query("create schema if not exists " ~ node.schema) %}
    {#
      `or replace`, not `if not exists`: ci.duckdb persists between local runs,
      so a changed column or data_type would otherwise be silently ignored --
      and stale types are the worst case, because unit tests introspect the
      relation and would keep passing against the old type. Safe only because
      of the target guard above.
    #}
    {% set ddl %}
      create or replace table {{ node.schema }}.{{ node.identifier }} (
        {%- for c in cols %}
        "{{ c.name }}" {{ c.data_type }}{{ "," if not loop.last }}
        {%- endfor %}
      )
    {% endset %}
    {% do run_query(ddl) %}
    {{ log("empty source: " ~ node.schema ~ "." ~ node.identifier, info=True) }}
  {% endfor %}
{% endmacro %}
