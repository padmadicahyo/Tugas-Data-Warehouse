
-- Data Mart DDL - PostgreSQL
DROP TABLE IF EXISTS fact_sales_item;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_order_status;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_ekspedisi;
DROP TABLE IF EXISTS dim_payment;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
  date_key INT PRIMARY KEY,
  full_date DATE NOT NULL UNIQUE,
  day INT, month_number INT, month_name VARCHAR(15),
  quarter INT, year INT, iso_week INT, day_name VARCHAR(15), is_weekend CHAR(1)
);

CREATE TABLE dim_customer (
  customer_key INT PRIMARY KEY,
  customer_id VARCHAR(20) NOT NULL,
  customer_name VARCHAR(120), email VARCHAR(160), gender CHAR(1), join_date DATE,
  street VARCHAR(160), city VARCHAR(80), province VARCHAR(80),
  effective_from DATE NOT NULL, effective_to DATE NOT NULL, is_current CHAR(1) NOT NULL
);

CREATE TABLE dim_seller (
  seller_key INT PRIMARY KEY,
  seller_id VARCHAR(20) UNIQUE NOT NULL,
  seller_name VARCHAR(140), seller_segment VARCHAR(30),
  street VARCHAR(160), city VARCHAR(80), province VARCHAR(80),
  join_date DATE, seller_status VARCHAR(20)
);

CREATE TABLE dim_product (
  product_key INT PRIMARY KEY,
  product_id VARCHAR(20) UNIQUE NOT NULL,
  product_name VARCHAR(180), brand VARCHAR(80), category VARCHAR(80), product_status VARCHAR(20)
);

CREATE TABLE dim_ekspedisi (
  expedition_key INT PRIMARY KEY,
  expedition_code VARCHAR(20) UNIQUE NOT NULL,
  expedition_name VARCHAR(120), base_shipping_fee BIGINT, sla_days INT
);

CREATE TABLE dim_payment (
  payment_key INT PRIMARY KEY,
  payment_method_code VARCHAR(20) UNIQUE NOT NULL,
  payment_method_name VARCHAR(80)
);

CREATE TABLE dim_order_status (
  status_key INT PRIMARY KEY,
  order_status VARCHAR(20), payment_status VARCHAR(20), shipment_status VARCHAR(20),
  promo_flag CHAR(1), bulk_order_flag CHAR(1), late_delivery_flag CHAR(1)
);

CREATE TABLE fact_sales (
  order_id VARCHAR(20) PRIMARY KEY,
  customer_key INT NOT NULL REFERENCES dim_customer(customer_key),
  seller_key INT NOT NULL REFERENCES dim_seller(seller_key),
  expedition_key INT NOT NULL REFERENCES dim_ekspedisi(expedition_key),
  payment_key INT NOT NULL REFERENCES dim_payment(payment_key),
  order_date_key INT NOT NULL REFERENCES dim_date(date_key),
  shipped_date_key INT REFERENCES dim_date(date_key),
  delivered_date_key INT REFERENCES dim_date(date_key),
  status_key INT NOT NULL REFERENCES dim_order_status(status_key),
  jumlah_item INT NOT NULL,
  total_quantity INT NOT NULL,
  gross_subtotal BIGINT NOT NULL,
  total_discount BIGINT NOT NULL,
  net_product_sales BIGINT NOT NULL,
  shipping_fee BIGINT NOT NULL,
  grand_total BIGINT NOT NULL,
  total_hpp BIGINT NOT NULL,
  profit BIGINT NOT NULL,
  delivery_days INT
);

CREATE TABLE fact_sales_item (
  sales_item_key BIGINT PRIMARY KEY,
  order_item_id VARCHAR(24) UNIQUE NOT NULL,
  order_id VARCHAR(20) NOT NULL,
  customer_key INT NOT NULL REFERENCES dim_customer(customer_key),
  seller_key INT NOT NULL REFERENCES dim_seller(seller_key),
  product_key INT NOT NULL REFERENCES dim_product(product_key),
  order_date_key INT NOT NULL REFERENCES dim_date(date_key),
  line_number INT NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  unit_price BIGINT NOT NULL,
  unit_hpp BIGINT NOT NULL,
  gross_subtotal BIGINT NOT NULL,
  allocated_discount BIGINT NOT NULL,
  net_sales BIGINT NOT NULL,
  total_hpp BIGINT NOT NULL,
  profit BIGINT NOT NULL,
  UNIQUE(order_id, line_number)
);

CREATE INDEX idx_fact_sales_date ON fact_sales(order_date_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_seller ON fact_sales(seller_key);
CREATE INDEX idx_fact_sales_status ON fact_sales(status_key);
CREATE INDEX idx_fact_sales_item_product ON fact_sales_item(product_key);
CREATE INDEX idx_fact_sales_item_order ON fact_sales_item(order_id);