-- all opened plots
SELECT w.name                      AS world,
       d.name                      AS district,
       ward_number + 1             AS ward_number,
       s.plot_number + 1           AS plot_number,
       CASE p.house_size
           WHEN 0 THEN 'SMALL'
           WHEN 1 THEN 'MEDIUM'
           WHEN 2 THEN 'LARGE' END AS house_size
FROM plot_states s
         LEFT JOIN plotinfo p ON s.territory_type_id = p.territory_type_id AND s.plot_number = p.plot_number
         LEFT JOIN districts d ON d.id = s.territory_type_id
         LEFT JOIN worlds w ON w.id = s.world_id
WHERE first_seen > 1643176800 -- 10PM, when world transfer opened
  AND first_seen < 1643184000 -- midnight, 2 hours later
  AND is_owned = FALSE
ORDER BY first_seen;

-- number by world
SELECT w.name          AS world,
       COUNT(world_id) AS count
FROM plot_states s
         LEFT JOIN worlds w ON w.id = s.world_id
WHERE first_seen > 1643176800 -- 10PM, when world transfer opened
  AND first_seen < 1643184000 -- midnight, 2 hours later
  AND is_owned = FALSE
GROUP BY w.name;

-- number by size
SELECT CASE p.house_size
           WHEN 0 THEN 'SMALL'
           WHEN 1 THEN 'MEDIUM'
           WHEN 2 THEN 'LARGE' END AS house_size,
       COUNT(p.house_size)         AS count
FROM plot_states s
         LEFT JOIN plotinfo p ON s.territory_type_id = p.territory_type_id AND s.plot_number = p.plot_number
WHERE first_seen > 1643176800 -- 10PM, when world transfer opened
  AND first_seen < 1643184000 -- midnight, 2 hours later
  AND is_owned = FALSE
GROUP BY p.house_size;

-- by world and size
SELECT w.name                          AS world,
       CASE p.house_size
           WHEN 0 THEN 'SMALL'
           WHEN 1 THEN 'MEDIUM'
           WHEN 2 THEN 'LARGE' END     AS house_size,
       COUNT((world_id, p.house_size)) AS count
FROM plot_states s
         LEFT JOIN plotinfo p ON s.territory_type_id = p.territory_type_id AND s.plot_number = p.plot_number
         LEFT JOIN worlds w ON w.id = s.world_id
WHERE first_seen > 1643176800 -- 10PM, when world transfer opened
  AND first_seen < 1643184000 -- midnight, 2 hours later
  AND is_owned = FALSE
GROUP BY w.name, p.house_size;
