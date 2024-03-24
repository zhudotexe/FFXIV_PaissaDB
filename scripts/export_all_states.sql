-- export_all_states
-- Exports all plot states ever seen.
-- all_states
SELECT s.id                        AS id,
       w.name                      AS world,
       d.name                      AS district,
       ward_number + 1             AS ward_number,
       s.plot_number + 1           AS plot_number,
       CASE p.house_size
           WHEN 0 THEN 'SMALL'
           WHEN 1 THEN 'MEDIUM'
           WHEN 2 THEN 'LARGE' END AS house_size,
       s.lotto_entries             AS lotto_entries,
       s.last_seen_price           AS price,
       s.first_seen                AS first_seen,
       s.last_seen                 AS last_seen,
       s.is_owned                  AS is_owned,
       MD5(s.owner_name)           AS owner_name_hash,
       s.owner_name LIKE '% %'     AS owner_name_has_space,
       s.lotto_phase               AS lotto_phase,
       s.lotto_phase_until         AS lotto_phase_until
FROM plot_states s
         LEFT JOIN plotinfo p ON s.territory_type_id = p.territory_type_id AND s.plot_number = p.plot_number
         LEFT JOIN districts d ON d.id = s.territory_type_id
         LEFT JOIN worlds w ON w.id = s.world_id
ORDER BY id DESC;
