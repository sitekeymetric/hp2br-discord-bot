-- Manual Cleanup of Pending Matches
-- Run this SQL to clean up pending matches older than 6 hours

-- First, let's see what we're about to clean up
SELECT 
    match_id,
    start_time,
    (julianday('now') - julianday(start_time)) * 24 as hours_old,
    total_teams,
    (SELECT COUNT(*) FROM match_players WHERE match_players.match_id = matches.match_id) as player_count
FROM matches 
WHERE status = 'PENDING' 
    AND (julianday('now') - julianday(start_time)) * 24 > 6
ORDER BY start_time DESC;

-- Uncomment the lines below to actually perform the cleanup:

-- Update matches to CANCELLED status
-- UPDATE matches 
-- SET status = 'CANCELLED', 
--     result_type = 'CANCELLED',
--     end_time = CURRENT_TIMESTAMP
-- WHERE status = 'PENDING' 
--     AND (julianday('now') - julianday(start_time)) * 24 > 6;

-- Update match players (optional - they can stay as PENDING)
-- UPDATE match_players 
-- SET result = 'PENDING'
-- WHERE match_id IN (
--     SELECT match_id FROM matches 
--     WHERE status = 'CANCELLED' 
--         AND result_type = 'CANCELLED'
-- );

-- Verify the cleanup
-- SELECT status, COUNT(*) FROM matches GROUP BY status;
