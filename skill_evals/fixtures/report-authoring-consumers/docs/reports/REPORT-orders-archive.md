# Orders archive table investigation

Synthetic fixture, not production findings. Report formats: Markdown only.

## Key findings

The orders service writes completed orders to the `orders_archive` table nightly. [E1](#E1)

## Consumers of orders_archive

The orders service is the only known writer. [E1](#E1)

## Evidence index

| ID | Source |
| --- | --- |
| <a id="E1"></a>E1 | [archive writer](../../repos/orders-service/src/archive.py) |
