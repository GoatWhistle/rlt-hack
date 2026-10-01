UPLOAD_COLUMNS = (
    "upload_id",
    "file_name",
    "total",
    "rejected",
    "issues",
    "created_at",
    "version",
    "is_deleted",
)
LOT_COLUMNS = (
    "upload_id",
    "lot_id",
    "position",
    "source_row",
    "title",
    "subject",
    "customer_inn",
    "publish_date",
    "start_price",
    "created_at",
    "version",
    "is_deleted",
)
RESULT_COLUMNS = (
    "upload_id",
    "lot_id",
    "status",
    "products",
    "candidates",
    "payload",
    "processed_at",
    "version",
    "is_deleted",
)

UPLOAD_FIELDS = "upload_id, file_name, total, issues, created_at"
LOT_FIELDS = "lot_id, source_row, title, subject, customer_inn, publish_date, start_price"

SELECT_RECENT = (
    "SELECT " + UPLOAD_FIELDS + " FROM {db}.uploads_current "
    "ORDER BY created_at DESC, upload_id LIMIT {{limit:UInt32}}"
)
SELECT_UPLOAD = (
    "SELECT " + UPLOAD_FIELDS + " FROM {db}.uploads_current "
    "WHERE upload_id = {{upload_id:UUID}} LIMIT 1"
)
SELECT_COUNTS = (
    "SELECT upload_id, status, count() FROM {db}.upload_results_current "
    "WHERE upload_id IN {{ids:Array(UUID)}} GROUP BY upload_id, status"
)
SELECT_LOTS = (
    "SELECT " + LOT_FIELDS + " FROM {db}.upload_lots_current "
    "WHERE upload_id = {{upload_id:UUID}} ORDER BY position"
)
SELECT_CHOSEN_LOTS = (
    "SELECT " + LOT_FIELDS + " FROM {db}.upload_lots_current "
    "WHERE upload_id = {{upload_id:UUID}} AND lot_id IN {{lot_ids:Array(String)}} "
    "ORDER BY position"
)
SELECT_STATES = (
    "SELECT lot_id, status, products, candidates FROM {db}.upload_results_current "
    "WHERE upload_id = {{upload_id:UUID}}"
)
SELECT_PAYLOADS = (
    "SELECT lot_id, payload FROM {db}.upload_results_current "
    "WHERE upload_id = {{upload_id:UUID}} AND lot_id IN {{lot_ids:Array(String)}}"
)
SELECT_PENDING = (
    "SELECT l.upload_id, l.lot_id, l.source_row, l.title, l.subject, l.customer_inn, "
    "l.publish_date, l.start_price FROM {db}.upload_lots_current AS l "
    "WHERE (l.upload_id, l.lot_id) NOT IN "
    "(SELECT upload_id, lot_id FROM {db}.upload_results_current) "
    "AND l.upload_id IN (SELECT upload_id FROM {db}.uploads_current) "
    "ORDER BY l.created_at, l.upload_id, l.position"
)
