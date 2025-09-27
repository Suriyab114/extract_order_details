# Sales Data ETL Pipeline

## Overview
This project demonstrates an ETL (Extract, Transform, Load) pipeline for encrypted regional sales data.

## Steps
1. **Extract**  
   - Reads sales files from Region A & B.  
   - Files are password-protected ZIPs containing `.csv` files.  
   - Passwords:  
     - Region A → `order_region_a`  
     - Region B → `order_region_b`  

2. **Transform**  
   - Business rules applied:  
     - Combine both regions.  
     - Add `total_sales = QuantityOrdered * ItemPrice`.  
     - Add `region` column.  
     - Drop duplicates based on `OrderId`.  
     - Add `net_sale = total_sales - PromotionDiscount`.  
     - Remove records with non-positive `net_sale`.  

3. **Load**  
   - Loads cleaned data into an SQLite database (`sales.db`) under table `sales_data`.

4. **Validation Queries**  
   - Count total records.  
   - Total sales by region.  
   - Average sales per transaction.  
   - Check duplicates by `OrderId`.  

## How to Run
```bash
pip install -r requirements.txt
python etl_pipeline.py
