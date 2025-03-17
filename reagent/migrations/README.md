alembic CLI is only used for development. cd to this directory first.

shared and namespace migrations use two different version tables. Branching was not working with me.
Branching of one table would be preferred for extensibility reasons and to make use of dependency feature.
Worst case scenario, always upgrade shared first as namespaces may depend on those tables but not vice versa.

new head:
alembic -n namespace revision --autogenerate -m "initial" --head=base
new revision:
alembic -n namespace revision --autogenerate -m "initial"
or
alembic -n shared revision --autogenerate -m "initial"