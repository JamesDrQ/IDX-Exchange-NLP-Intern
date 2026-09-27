import mysql.connector
import pandas as pd

conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="rootpass",
    database="real_estate",
)

query = """
SELECT
    L_ListingID,
    L_Address,
    L_City,
    L_Keyword2 AS beds,
    LM_Dec_3 AS baths,
    L_SystemPrice AS price,
    L_Remarks AS remarks
FROM rets_property
WHERE L_Remarks IS NOT NULL
  AND LENGTH(L_Remarks) > 50
ORDER BY RAND()
LIMIT 1000
"""

df = pd.read_sql(query, conn)

df.to_csv(
    "data/processed/listing_sample.csv",
    index=False
)

conn.close()

print(f"Saved {len(df)} listings")