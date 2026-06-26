import re
from datetime import datetime
from .erp_connector import query
from django.core.cache import cache

def extract_family(name):
    """
    Extracts the product family (e.g. GÖDƏKÇƏ, POLO) from a complex product string.
    Example: 'HM-BETEX/01/0119 GÖDƏKÇƏ FƏHLƏ BOZ R-46' -> 'GÖDƏKÇƏ'
    """
    parts = name.split()
    for p in parts:
        # Ignore codes, codes with slashes, size identifiers (R-46), and pure numbers
        if '/' not in p and 'HM-' not in p and 'YM-' not in p and len(p) > 2 and not p.startswith('R-') and not any(char.isdigit() for char in p):
            return p.upper()
    return "DİGƏR"

def get_throughput_rates():
    """
    Calculates the historical baseline pieces/day produced for each product family.
    Uses ERP transfer data to find total produced over total time.
    """
    cached = cache.get('workwear_throughput_rates')
    if cached:
        return cached
        
    sql = """
    WITH HM_Goods AS (
        SELECT idn, name, muddet, SUBSTRING(name, 4, LEN(name)) as base_name
        FROM sm_goods WITH (NOLOCK)
        WHERE class = 27 AND muddet > 0 AND name LIKE 'HM-%'
    ),
    YM_Goods AS (
        SELECT idn, name, SUBSTRING(name, 4, LEN(name)) as base_name
        FROM sm_goods WITH (NOLOCK)
        WHERE name LIKE 'YM-%'
    )
    SELECT 
        hm.name AS product_name,
        hm.muddet,
        MIN(t.tarix) AS first_date,
        MAX(t.tarix) AS last_date,
        SUM(tel.miqdar) AS total_produced
    FROM HM_Goods hm
    JOIN YM_Goods ym ON ym.base_name = hm.base_name
    JOIN sm_sob_trans_el tel WITH (NOLOCK) ON tel.mal = ym.idn
    JOIN sm_sob_trans t WITH (NOLOCK) ON t.idn = tel.es_no
    WHERE t.tesdiq = 1 AND t.sobe2 = 6
    GROUP BY hm.name, hm.muddet
    
    UNION ALL
    
    SELECT 
        hm.name AS product_name,
        hm.muddet,
        MIN(t.tarix) AS first_date,
        MAX(t.tarix) AS last_date,
        SUM(tel.miqdar) AS total_produced
    FROM sm_goods hm WITH (NOLOCK)
    JOIN sm_sob_trans_el tel WITH (NOLOCK) ON tel.mal = hm.idn
    JOIN sm_sob_trans t WITH (NOLOCK) ON t.idn = tel.es_no
    WHERE hm.class = 27 AND hm.muddet > 0 AND t.tesdiq = 1 AND t.sobe2 = 6
    GROUP BY hm.name, hm.muddet
    """
    try:
        rows = query(sql)
    except Exception as e:
        print(f"Error fetching throughput data: {e}")
        return {}
    
    families = {}
    for r in rows:
        fam = extract_family(r['product_name'])
        if fam not in families:
            families[fam] = {
                'total_produced': 0,
                'min_date': None,
                'max_date': None,
                'sum_muddet': 0,
                'muddet_count': 0
            }
        
        families[fam]['total_produced'] += float(r['total_produced'])
        families[fam]['sum_muddet'] += float(r['muddet'])
        families[fam]['muddet_count'] += 1
        
        if not families[fam]['min_date'] or r['first_date'] < families[fam]['min_date']:
            families[fam]['min_date'] = r['first_date']
        if not families[fam]['max_date'] or r['last_date'] > families[fam]['max_date']:
            families[fam]['max_date'] = r['last_date']
            
    rates = {}
    for fam, data in families.items():
        if data['min_date'] and data['max_date']:
            delta = (data['max_date'] - data['min_date']).days
            
            # If a product was made in a single day, assign at least 1 working day
            if delta < 1:
                delta = 1
                
            # Convert calendar days to working days (roughly 5 out of 7 days a week)
            working_days = max(1, int(delta * (5/7.0)))
            
            avg_muddet = data['sum_muddet'] / max(1, data['muddet_count'])
            pieces_per_day = data['total_produced'] / working_days
            
            # Only store valid rates
            if pieces_per_day > 0:
                rates[fam] = {
                    'pieces_per_day': round(pieces_per_day, 1),
                    'avg_muddet': round(avg_muddet, 1)
                }
            
    # Save to cache for 24 hours (86400 seconds)
    cache.set('workwear_throughput_rates', rates, 86400)
    return rates
