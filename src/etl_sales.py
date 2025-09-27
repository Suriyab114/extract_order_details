import os
import sqlite3
import pandas as pd
import pyzipper

DB_NAME = "order_details.db"

# -------------------------------
# 1. Extract Step
# -------------------------------
def read_encrypted_csv(zip_path, password):
    """Read password-protected ZIP containing a CSV and return DataFrame."""
    with pyzipper.AESZipFile(zip_path) as zf:
        zf.pwd = password.encode()
        csv_name = zf.namelist()[0]  # assume only one CSV inside
        with zf.open(csv_name) as f:
            df = pd.read_csv(f)
    return df


def extract_data(file_a, pass_a, file_b, pass_b):
    df_a = read_encrypted_csv(file_a, pass_a)
    df_a["region"] = "A"

    df_b = read_encrypted_csv(file_b, pass_b)
    df_b["region"] = "B"

    combined = pd.concat([df_a, df_b], ignore_index=True)
    return combined


# -------------------------------
# 2. Transform Step
# -------------------------------
def transform_data(df):
    # Business rules
    df["total_sales"] = df["QuantityOrdered"] * df["ItemPrice"]
    df["net_sale"] = df["total_sales"] - df["PromotionDiscount"]

    # Remove duplicates based on OrderId (keep first occurrence)
    df = df.drop_duplicates(subset=["OrderId"], keep="first")

    # Exclude orders where net_sale <= 0
    df = df[df["net_sale"] > 0]

    return df


# -------------------------------
# 3. Load Step
# -------------------------------
def create_order_details_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_data (
            OrderId TEXT PRIMARY KEY,
            OrderItemId TEXT,
            QuantityOrdered INTEGER,
            ItemPrice REAL,
            PromotionDiscount REAL,
            total_sales REAL,
            region TEXT,
            net_sale REAL
        )
    """)
    conn.commit()
    conn.close()


def load_data(df):
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("sales_data", conn, if_exists="replace", index=False)
    conn.close()


# -------------------------------
# 4. Validation Queries
# -------------------------------
def run_validation_queries():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("\n--- Validation Queries ---")

    # a. Count total records
    cursor.execute("SELECT COUNT(*) FROM sales_data")
    print("Total records:", cursor.fetchone()[0])

    # b. Total sales amount by region
    cursor.execute("SELECT region, SUM(net_sale) FROM sales_data GROUP BY region")
    print("Total sales by region:", cursor.fetchall())

    # c. Average sales amount per transaction
    cursor.execute("SELECT AVG(net_sale) FROM sales_data")
    print("Average sales per transaction:", cursor.fetchone()[0])

    # d. Ensure no duplicate OrderIds
    cursor.execute("""
        SELECT OrderId, COUNT(*) 
        FROM sales_data 
        GROUP BY OrderId 
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        print("Duplicate OrderIds found:", duplicates)
    else:
        print("No duplicate OrderIds found.")

    conn.close()


# -------------------------------
# 5. Main ETL Pipeline
# -------------------------------
def main():
    file_a = "data/order_region_a.zip"
    file_b = "data/order_region_b.zip"
    pass_a = "order_region_a"
    pass_b = "order_region_b"

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Removed previous database file: {DB_NAME}")

    print("\n--- Starting ETL Pipeline ---")

    try:
        extracted = extract_data(file_a, pass_a, file_b, pass_b)
        transformed = transform_data(extracted)
        create_order_details_table()
        load_data(transformed)
        run_validation_queries()
        print("\n--- ETL Pipeline Completed Successfully ---")
    except Exception as e:
        print(f"\n--- FATAL ERROR ---\n{e}")


if __name__ == "__main__":
    main()
