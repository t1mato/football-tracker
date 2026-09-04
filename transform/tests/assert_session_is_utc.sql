{#
  The profile pins TimeZone: 'UTC', but a profile is config anyone can
  change. This makes that change loud.

  Guarded by target.type because current_setting() is DuckDB syntax and
  would be a syntax error on BigQuery -- an unguarded guard against the
  warehouse swap would itself break the swap.

  Note this only runs under dbt test/build. A bare dbt run with a bad
  session still produces wrong data, which is why correctness rests on the
  naive-timestamp normalisation in stg_matches rather than on this test.
#}
{% if target.type == 'duckdb' %}
select current_setting('TimeZone') as session_timezone
where current_setting('TimeZone') <> 'UTC'
{% else %}
select 1 where false
{% endif %}
