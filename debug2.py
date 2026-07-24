import psycopg2, pandas as pd
conn = psycopg2.connect('postgresql://user:password@localhost:5434/erg_opera_data')

q = """
SELECT 
    s.transaction_code,
    s.revenue_category as current_category,
    t.classification,
    t.transaction_group,
    SUM(s.net_amount) as total
FROM analytics.stg_cashiering_postings s
LEFT JOIN analytics.stg_transaction_codes t ON s.transaction_code = t.transaction_code
WHERE s.revenue_date BETWEEN '2026-07-01' AND '2026-07-31'
GROUP BY 1, 2, 3, 4
ORDER BY 5 DESC
"""
df = pd.read_sql(q, conn)

# Current sums
print("Current DB:")
print(df.groupby('current_category')['total'].sum())

# Target sums
target = {
    'Room': 1107954458,
    'FnB': 2430030588,
    'Other': 15660173
}

# Find which combinations of codes can fix the difference.
# Diff we need to apply:
diff = {
    'Room': target['Room'] - df[df['current_category'] == 'Room']['total'].sum(),
    'FnB': target['FnB'] - df[df['current_category'] == 'FnB']['total'].sum(),
    'Other': target['Other'] - df[df['current_category'] == 'Other']['total'].sum()
}
print("\nRequired Changes:")
print(diff)

print("\nAll codes sorted by transaction code:")
print(df.sort_values('transaction_code').to_string(index=False))
