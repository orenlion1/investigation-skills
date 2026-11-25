-- Synthetic fixture: daily revenue from the live orders table.
SELECT date(closed_at) AS day, sum(total) AS revenue
FROM orders
WHERE status = 'closed'
GROUP BY day;
