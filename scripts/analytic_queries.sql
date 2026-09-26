-- ============================================================
-- ANALYTIC QUERIES - ELECTRONIC COMMERCE DATA MART
-- ============================================================

-- Q1. 
SELECT
    s.seller_id,
    s.seller_name,
    COUNT(f.order_id) AS total_orders,
    SUM(f.net_product_sales) AS revenue,
    SUM(f.profit) AS profit
FROM fact_sales f
JOIN dim_seller s ON f.seller_key = s.seller_key
JOIN dim_order_status st ON f.status_key = st.status_key
WHERE st.order_status = 'COMPLETED'
GROUP BY s.seller_name,s.seller_id
ORDER BY profit DESC LIMIT 5;

-- Q2. Kategori dengan penjualan dan profit terbesar
SELECT
    d.year,
    d.month_number,
    d.month_name,
    COUNT(*) AS total_orders,
    SUM(f.net_product_sales)/1000000000 AS net_product_sales_miliar,
    SUM(f.profit)/1000000 AS profit_juta,
FROM fact_sales f
JOIN dim_date d ON f.order_date_key = d.date_key
JOIN dim_order_status st ON f.status_key = st.status_key
WHERE st.order_status <> 'CANCELLED'
GROUP BY d.year, d.month_number, d.month_name
ORDER BY d.year, d.month_number;

-- Q3. Top seller berdasarkan profit
SELECT 
    c.province AS customer_province,
    COUNT(f.order_id) AS total_orders,
    SUM(f.net_product_sales)/ 1000000.0 AS revenue_juta,
    SUM(f.profit) / 1000000.0 AS profit_juta
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
JOIN dim_order_status st ON f.status_key = st.status_key
WHERE st.order_status = 'COMPLETED'
GROUP BY c.province
ORDER BY profit_juta DESC;

-- Q4. Performa ekspedisi: delivery time dan late rate
SELECT
    p.category,
    SUM(i.quantity) AS units_sold,
    SUM(i.net_sales) / 1000000000.0 AS net_sales_miliar,
    SUM(i.profit) / 1000000000.0 AS profit_miliar
FROM fact_sales_item i
JOIN dim_product p ON i.product_key = p.product_key
JOIN fact_sales f ON i.order_id = f.order_id
JOIN dim_order_status st ON f.status_key = st.status_key
JOIN dim_date d ON f.order_date_key = d.date_key
WHERE st.order_status = 'COMPLETED'
  AND d.is_weekend = 'Y'
GROUP BY p.category
ORDER BY units_sold DESC

-- Q5. Metode pembayaran dan payment success rate
SELECT
        e.expedition_code,
        e.expedition_name,
        COUNT(DISTINCT f.order_id) AS total_orders
FROM fact_sales f
JOIN dim_customer c
        ON f.customer_key = c.customer_key
JOIN dim_ekspedisi e
        ON f.expedition_key = e.expedition_key
JOIN dim_order_status st
        ON f.status_key = st.status_key
WHERE st.order_status = 'COMPLETED'
      AND UPPER(TRIM(c.province)) = 'JAWA TENGAH'
GROUP BY
        e.expedition_code,
        e.expedition_name
ORDER BY total_orders DESC;
