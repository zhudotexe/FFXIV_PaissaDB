-- export_lottery_stats
-- Exports the entry stats from the most recent entry cycle, ordered by entry count descending.
WITH constants (lotto_cycle, cycle_mod)
         AS (VALUES (777600, 54000))
-- ^ set to seconds in 9 days, offset within 9-day cycle (e.g. 1658674800 % 777600 = 54000)
SELECT w.name                      AS world,
       d.name                      AS district,
       ward_number + 1             AS ward_number,
       s.plot_number + 1           AS plot_number,
       CASE p.house_size
           WHEN 0 THEN 'SMALL'
           WHEN 1 THEN 'MEDIUM'
           WHEN 2 THEN 'LARGE' END AS house_size,
       s.lotto_entries             AS lotto_entries,
       s.last_seen_price           AS price
FROM plot_states s
         LEFT JOIN plotinfo p ON s.territory_type_id = p.territory_type_id AND s.plot_number = p.plot_number
         LEFT JOIN districts d ON d.id = s.territory_type_id
         LEFT JOIN worlds w ON w.id = s.world_id
         JOIN constants ON TRUE
WHERE lotto_phase_until =
      FLOOR((EXTRACT(EPOCH FROM NOW()) - constants.cycle_mod) / constants.lotto_cycle) * constants.lotto_cycle +
      constants.cycle_mod
ORDER BY lotto_entries DESC NULLS LAST;
