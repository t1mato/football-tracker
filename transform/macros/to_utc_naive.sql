{#
  Convert a timestamptz to a NAIVE timestamp holding the UTC wall clock.

  This is the whole UTC strategy. DuckDB resolves date and hour extraction
  against the session timezone, so deriving them from a timestamptz gives
  session-dependent answers -- 1,119 of 7,655 matches land on the wrong day
  under a US session. Normalising once here means downstream date() and
  extract() operate on a naive value and are session-independent in both
  warehouses, so there is no macro for anyone to remember to call.

  A plain target.type branch, not adapter.dispatch: dispatch exists so
  package consumers can override a macro, and nothing consumes this project.
#}
{% macro to_utc_naive(column) -%}
  {%- if target.type == 'bigquery' -%}
    datetime({{ column }}, 'UTC')
  {%- else -%}
    ({{ column }} at time zone 'UTC')
  {%- endif -%}
{%- endmacro %}
