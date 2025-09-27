import os
import sqlite3
import pandas as pd
import json

DB_NAME = "order_details.db"

# -------------------------------
# 1. Extract Step
# -------------------------------
def extract_data(file_a, file_b):
    """Read CSV files from Region A and B."""
    df_a = pd.read_csv(file_a)
    df_a["region"] = "A"

    df_b = pd.read_csv(file_b)
    df_b["region"] = "B"

    combined = pd.concat([df_a, df_b], ignore_index=True)
    print(combined.head())
    return combined


# -------------------------------
# 2. Transform csv to json 
# -------------------------------
def clean_promotion_discount(df):
    """Convert PromotionDiscount JSON string to numeric Amount."""
    def extract_amount(x):
        try:
            # Some CSVs have quotes, so remove extra quotes
            if isinstance(x, str):
                x = x.replace('""', '"')
                data = json.loads(x)
                return float(data["Amount"])
            return 0.0
        except Exception:
            return 0.0
    df["PromotionDiscount"] = df["PromotionDiscount"].apply(extract_amount)
    return df



# -------------------------------
# 3. Transform Step
# -------------------------------
def transform_data(df):
    df = clean_promotion_discount(df)

    # Ensure other columns are numeric
    df["QuantityOrdered"] = pd.to_numeric(df["QuantityOrdered"], errors="coerce")
    df["ItemPrice"] = pd.to_numeric(df["ItemPrice"], errors="coerce")

    # Drop rows with missing essential values
    df = df.dropna(subset=["QuantityOrdered", "ItemPrice", "PromotionDiscount"])

    # Apply business rules
    df["total_sales"] = df["QuantityOrdered"] * df["ItemPrice"]
    df["net_sale"] = df["total_sales"] - df["PromotionDiscount"]

    # Drop duplicates based on OrderId
    df = df.drop_duplicates(subset=["OrderId"], keep="first")

    # Remove rows where net_sale <= 0
    df = df[df["net_sale"] > 0]

    return df


# -------------------------------
# 4. Load Step
# -------------------------------
def create_order_details_table():
    """Create SQLite table order_details."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_details (
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
    """Load transformed DataFrame into SQLite."""
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("order_details", conn, if_exists="replace", index=False)
    conn.close()


# -------------------------------
# 5. Validation Queries
# -------------------------------
def run_validation_queries():
    """Run SQL queries to validate loaded data."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("\n--- Validation Queries ---")

    # a. Count total records
    cursor.execute("SELECT COUNT(*) FROM order_details")
    print("Total records:", cursor.fetchone()[0])

    # b. Total sales by region
    cursor.execute("SELECT region, SUM(net_sale) FROM order_details GROUP BY region")
    print("Total sales by region:", cursor.fetchall())

    # c. Average sales per transaction
    cursor.execute("SELECT AVG(net_sale) FROM order_details")
    print("Average sales per transaction:", cursor.fetchone()[0])

    # d. Duplicate OrderIds
    cursor.execute("""
        SELECT OrderId, COUNT(*) 
        FROM order_details 
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
# 6. Main ETL Pipeline
# -------------------------------
def main():
    # ✅ Use raw string for Windows paths (or escape backslashes)
    file_a = "order_region_a.csv"
    file_b = "order_region_b.csv"

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Removed previous database file: {DB_NAME}")

    print("\n--- Starting ETL Pipeline ---")

    try:
        extracted = extract_data(file_a, file_b)
        transformed = transform_data(extracted)
        create_order_details_table()
        load_data(transformed)
        run_validation_queries()
        print("\n--- ETL Pipeline Completed Successfully ---")
    except Exception as e:
        print(f"\n--- FATAL ERROR ---\n{e}")


if __name__ == "__main__":
    main()