{#
  Creates empty tables for every declared source.

  dbt unit tests introspect the source relation to learn column types, so
  they cannot run at all when the relation is absent -- declaring data_type
  in YAML does NOT substitute, that was tried and fails identically. The
  relation must exist but may be empty, which is exactly what CI needs.

  Reading graph.sources makes _sources.yml the single source of truth: no
  parallel DDL file to drift, no CSV fixtures to hand-maintain, no binary
  database in git.
#}
{% macro create_empty_sources() %}
  {% for node in graph.sources.values() %}
    {% set cols = node.columns.values() | list %}
    {% if cols %}
      {% do run_query("create schema if not exists " ~ node.schema) %}
      {% set ddl %}
        create table if not exists {{ node.schema }}.{{ node.identifier }} (
          {%- for c in cols %}
          "{{ c.name }}" {{ c.data_type }}{{ "," if not loop.last }}
          {%- endfor %}
        )
      {% endset %}
      {% do run_query(ddl) %}
      {{ log("empty source: " ~ node.schema ~ "." ~ node.identifier, info=True) }}
    {% endif %}
  {% endfor %}
{% endmacro %}
