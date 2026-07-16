import re
with open('DASHBOARD_MOCKUP_V3.html', 'r') as f:
    content = f.read()
match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if match:
    js = match.group(1)
    open_paren = js.count('(')
    close_paren = js.count(')')
    open_brace = js.count('{')
    close_brace = js.count('}')
    open_bracket = js.count('[')
    close_bracket = js.count(']')
    print(f'Parens: {open_paren} open, {close_paren} close, diff: {open_paren - close_paren}')
    print(f'Braces: {open_brace} open, {close_brace} close, diff: {open_brace - close_brace}')
    print(f'Brackets: {open_bracket} open, {close_bracket} close, diff: {open_bracket - close_bracket}')
    for var in ['const gradientFn', 'const dates', 'const weeks', 'const paceLabels', 'const leadBins', 'const chartColors', 'const colorMap', 'const kpiData']:
        count = js.count(var)
        print(f'{var}: {count} occurrences')