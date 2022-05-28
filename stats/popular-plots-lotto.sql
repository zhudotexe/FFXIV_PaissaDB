-- most popular houses by lotto entry
SELECT w.name                                         AS world,
       d.name                                         AS district,
       ward_number + 1                                AS ward_number,
       s.plot_number + 1                              AS plot_number,
       CASE p.house_size
           WHEN 0 THEN 'SMALL'
           WHEN 1 THEN 'MEDIUM'
           WHEN 2 THEN 'LARGE' END                    AS house_size,
       s.lotto_entries                                AS lotto_entries,
       (s.lotto_entries * p.house_base_price::bigint) AS total_gil_sunk
FROM plot_states s
         LEFT JOIN plotinfo p ON s.territory_type_id = p.territory_type_id AND s.plot_number = p.plot_number
         LEFT JOIN districts d ON d.id = s.territory_type_id
         LEFT JOIN worlds w ON w.id = s.world_id
WHERE lotto_phase_until = 1654009200
ORDER BY total_gil_sunk DESC NULLS LAST;
