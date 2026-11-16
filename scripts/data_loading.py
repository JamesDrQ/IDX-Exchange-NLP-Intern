"""Export a local listing sample using explicit environment credentials."""
from pathlib import Path
import mysql.connector
import pandas as pd

if __package__:
    from .database_config import mysql_settings
else:
    from database_config import mysql_settings

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


def load_sample(output="data/processed/listing_sample.csv"):
    settings = mysql_settings()  # Validate before attempting a connection.
    conn = mysql.connector.connect(**settings)
    try:
        df = pd.read_sql(query, conn)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        return len(df)
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"Saved {load_sample()} listings")
