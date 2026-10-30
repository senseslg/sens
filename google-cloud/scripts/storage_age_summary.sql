-- Read-only summary of existing Storage Insights metadata, never file contents.
-- Freeze the cutoff when reviewing a specific cleanup plan; this is not deletion SQL.
SELECT
  bucket,
  CASE WHEN softDeleteTime IS NOT NULL THEN 'soft_deleted'
       WHEN timeDeleted IS NOT NULL THEN 'deleted_or_noncurrent'
       ELSE 'live_or_noncurrent' END AS object_state,
  COUNT(*) AS object_versions,
  ROUND(SUM(size) / POW(1024, 3), 3) AS gib,
  COUNTIF(timeCreated < TIMESTAMP('2024-10-24 00:00:00', 'Asia/Phnom_Penh')) AS created_before_cutoff,
  ROUND(SUM(IF(timeCreated < TIMESTAMP('2024-10-24 00:00:00', 'Asia/Phnom_Penh'), size, 0)) / POW(1024, 3), 3) AS old_created_gib,
  ROUND(SUM(IF(updated < TIMESTAMP('2024-10-24 00:00:00', 'Asia/Phnom_Penh'), size, 0)) / POW(1024, 3), 3) AS old_updated_gib,
  MIN(snapshotTime) AS oldest_snapshot,
  MAX(snapshotTime) AS newest_snapshot
FROM `cambodian-express.project_2026_01_12_20_39_03_97fb30e9_48b7_4533_b454_3ab489f155b9.object_attributes_latest_snapshot_view`
GROUP BY bucket, object_state
ORDER BY gib DESC;
