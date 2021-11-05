-- Used to generate a breakdown of the worlds and districts that larger houses are more likely to appear in.

-- Grouped by world
SELECT (SELECT name FROM worlds WHERE worlds.id = sales.world_id) AS world_name,
       COUNT(*)                                                   AS non_small_sale_count
FROM sales
         LEFT JOIN plotinfo ON (sales.territory_type_id = plotinfo.territory_type_id AND
                                sales.plot_number = plotinfo.plot_number)
WHERE plotinfo.house_size > 0
GROUP BY world_id;

-- Grouped by district
SELECT (SELECT name FROM districts WHERE districts.id = sales.territory_type_id) AS district_name,
       COUNT(*)                                                                  AS non_small_sale_count
FROM sales
         LEFT JOIN plotinfo ON (sales.territory_type_id = plotinfo.territory_type_id AND
                                sales.plot_number = plotinfo.plot_number)
WHERE plotinfo.house_size > 0
GROUP BY sales.territory_type_id;

-- Grouped by district and world
SELECT (SELECT name FROM worlds WHERE worlds.id = sales.world_id)                AS world_name,
       (SELECT name FROM districts WHERE districts.id = sales.territory_type_id) AS district_name,
       COUNT(*)                                                                  AS non_small_sale_count
FROM sales
         LEFT JOIN plotinfo ON (sales.territory_type_id = plotinfo.territory_type_id AND
                                sales.plot_number = plotinfo.plot_number)
WHERE plotinfo.house_size > 0
GROUP BY world_id, sales.territory_type_id;