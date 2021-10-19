-- Used to generate a list of most popular plots by number of times seen, and how many times they have been
-- sold/reloed into. Requires sales.csv as a table named `sales`.

-- popular plots
SELECT (SELECT name FROM districts d WHERE d.id = s.territory_type_id)      AS district,
       s.plot_number + 1                                                    AS plot,
       COUNT(*)                                                             AS times_seen,
       COUNT(CASE WHEN is_relo = TRUE THEN 1 END)                           AS times_reloed,
       COUNT(CASE WHEN is_relo = FALSE THEN 1 END)                          AS times_sold,
       CASE (SELECT p.house_size
             FROM plotinfo p
             WHERE p.territory_type_id = s.territory_type_id
               AND p.plot_number = s.plot_number)
           WHEN 0 THEN 'SMALL'
           WHEN 1 THEN 'MEDIUM'
           WHEN 2 THEN 'LARGE' END                                          AS house_size,
       ROUND(AVG(s.known_price), 0)                                         AS avg_sale_price,
       COUNT(CASE WHEN is_relo = TRUE THEN 1 END) / CAST(COUNT(*) AS float) AS relo_ratio
FROM sales s
GROUP BY (s.territory_type_id, s.plot_number)
ORDER BY times_seen DESC;

-- plots without a recorded sale
SELECT (SELECT name FROM districts d WHERE d.id = territory_type_id),
       plot_number + 1,
       house_size
FROM plotinfo
WHERE (territory_type_id, plot_number) NOT IN (SELECT territory_type_id, plot_number FROM sales);
