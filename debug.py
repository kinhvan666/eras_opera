import psycopg2, pandas as pd
conn = psycopg2.connect('postgresql://user:password@localhost:5434/erg_opera_data')
q = """
SELECT 
    s.transaction_code,
    s.revenue_category,
    t.classification,
    t.transaction_group,
    SUM(s.net_amount) as total,
    SUM(s.posted_amount) as total_posted
FROM analytics.stg_cashiering_postings s
LEFT JOIN analytics.stg_transaction_codes t ON s.transaction_code = t.transaction_code
WHERE s.revenue_date BETWEEN '2026-07-01' AND '2026-07-31'
GROUP BY 1, 2, 3, 4
ORDER BY 5 DESC
"""
pd.set_option('display.max_rows', None)
print(pd.read_sql(q, conn))
