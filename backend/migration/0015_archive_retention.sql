ALTER TABLE supplier_search.searches MODIFY TTL toDateTime(created_at) + INTERVAL 180 DAY;
