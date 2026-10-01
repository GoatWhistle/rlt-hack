SUPPLIERS_BY_ITEM = """
SELECT s.supplier_id, s.inn, s.name, o.offer_id, m.confidence
FROM supplier_search.offer_matches_current AS m
INNER JOIN supplier_search.offers_current AS o ON o.offer_id = m.offer_id
INNER JOIN supplier_search.suppliers_current AS s ON s.supplier_id = o.supplier_id
WHERE m.catalog_item_id = {catalog_item_id:UUID}
  AND m.status = 'accepted'
  AND m.offer_content_hash = o.content_hash
  AND o.seller_status = 'verified'
  AND s.identity_status = 'verified'
ORDER BY m.confidence DESC, s.supplier_id, o.offer_id
"""

NEAREST_ITEMS = """
SELECT entity_id, cosineDistance(embedding, {query_vector:Array(Float32)}) AS distance
FROM supplier_search.embeddings_current
WHERE entity_type = 'catalog_item'
  AND model_key = {model_key:String}
  AND dimensions = length({query_vector:Array(Float32)})
ORDER BY distance, entity_id
LIMIT 20
"""
