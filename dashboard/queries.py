"""
queries.py — All SQL queries for the Socks Dashboard.
Socks classes: 21 (CORAB), 29 (QADIN CORABI), 30 (UŞAQ CORABI)
Socks warehouses: 2 (Raw Mat), 6 (Finished Goods), 7 (Binə Store),
                  11 (Sədərək Store), 17 (Workshop), 18 (Staging)
"""
import pyodbc
from django.core.cache import cache
import json
import copy
from .erp_connector import query, query_one
from .queue_engine import calculate_active_queue_dates

def get_dynamic_ym_ids(sector='isci'):
    cache_key = f'dynamic_ym_ids_{sector}'
    cached_ids = cache.get(cache_key)
    if cached_ids is not None:
        return cached_ids

    sql = "SELECT idn, name, class FROM sm_goods WITH (NOLOCK)"
    try:
        rows = query(sql)
    except Exception:
        return "0"
        
    target_classes = {21, 29, 30}
    if sector == 'underwear':
        target_classes = {18, 20}
    elif sector == 'isci':
        target_classes = {22, 24, 27, 31, 32, 34}
        
    hm_prefixes = set()
    for r in rows:
        cls = r['class']
        name = r['name'] or ''
        if cls in target_classes and name.startswith('HM-'):
            prefix = name.split('/')[0].split(' ')[0]
            hm_prefixes.add(prefix)
            
    matched_ids = []
    for r in rows:
        if r['class'] is None:
            name = r['name'] or ''
            if name.startswith('TM-'):
                base_name = name.split('/')[0].split(' ')[0]
                hm_equiv = base_name.replace('TM-', 'HM-', 1)
                if hm_equiv in hm_prefixes:
                    matched_ids.append(str(r['idn']))
            elif name.startswith('HM-'):
                hm_equiv = name.split('/')[0].split(' ')[0]
                if hm_equiv in hm_prefixes:
                    matched_ids.append(str(r['idn']))
                    
    matched_ids_str = ",".join(matched_ids) if matched_ids else "0"
    cache.set(cache_key, matched_ids_str, 3600)  # Cache for 1 hour
    return matched_ids_str

def get_sector_rules(sector):
    ym_ids_str = get_dynamic_ym_ids(sector)
    if sector == 'isci':
        class_condition = f"(g.class IN (22, 24, 27, 31, 32, 34) OR g.idn IN ({ym_ids_str}))"
        class_condition_ym = f"(ym_g.class IN (22, 24, 27, 31, 32, 34) OR ym_g.idn IN ({ym_ids_str}))"
        return {
            'classes': '(22, 24, 27, 31, 32, 34)',
            'class_condition': class_condition,
            'class_condition_ym': class_condition_ym,
            'dept_priority': [6, 15, 39, 5, 4, 3, 24, 8, 9],
            'raw_dept': "'42'",
            'stage_list_keys': ['0', '1', '2', '3', '4'],
            'stage_names': {
                '0': 'Satış (sifariş)',
                '1': 'Material təchizatı',
                '2': 'Kəsim',
                '3': 'Tikiş',
                '4': 'Hazır Məhsul'
            },
            'stages': {
                'all': {'id': 'all', 'name': 'Kapasitə (Ümumi)', 'count': 0, 'cap': 650, 'pct': 0},
                '0': {'id': '0', 'name': 'Satış (sifariş)', 'count': 0, 'cap': 200, 'pct': 0},
                '1': {'id': '1', 'name': 'Material təchizatı', 'count': 0, 'cap': 150, 'pct': 0},
                '2': {'id': '2', 'name': 'Kəsim', 'count': 0, 'cap': 150, 'pct': 0},
                '3': {'id': '3', 'name': 'Tikiş', 'count': 0, 'cap': 150, 'pct': 0},
                '4': {'id': '4', 'name': 'Hazır Məhsul', 'count': 0, 'cap': 150, 'pct': 0},
            }
        }
    elif sector == 'underwear':
        class_condition = f"(g.class IN (18, 20) OR g.idn IN ({ym_ids_str}))"
        class_condition_ym = f"(ym_g.class IN (18, 20) OR ym_g.idn IN ({ym_ids_str}))"
        return {
            'classes': '(18, 20)',
            'class_condition': class_condition,
            'class_condition_ym': class_condition_ym,
            'warehouses': '(2, 6, 7, 11, 17, 18)',
            'stages': {
                'all': {'id': 'all', 'name': 'Kapasitə (Ümumi)', 'count': 0, 'cap': 650, 'pct': 0},
                '0': {'id': '0', 'name': 'Satış (sifariş)', 'count': 0, 'cap': 200, 'pct': 0},
                '1': {'id': '1', 'name': 'Material', 'count': 0, 'cap': 150, 'pct': 0},
                '2': {'id': '2', 'name': 'Kəsim', 'count': 0, 'cap': 150, 'pct': 0},
                '3': {'id': '3', 'name': 'Tikiş', 'count': 0, 'cap': 150, 'pct': 0},
                '4': {'id': '4', 'name': 'Hazır Məhsul', 'count': 0, 'cap': 150, 'pct': 0},
            },
            'stage_list_keys': ['all', '0', '1', '2', '3', '4'],
            'dept_priority': [6, 15, 39, 5, 4, 3, 24, 8, 9],
            'color': 'acc',
            'bg': 'rgba(91,173,240,.05)'
        }
    else: # corab
        class_condition = f"(g.class IN (21, 29, 30) OR g.idn IN ({ym_ids_str}))"
        class_condition_ym = f"(ym_g.class IN (21, 29, 30) OR ym_g.idn IN ({ym_ids_str}))"
        return {
            'classes': '(21, 29, 30)',
            'class_condition': class_condition,
            'class_condition_ym': class_condition_ym,
            'warehouses': '(2, 6, 7, 11, 17, 18)',
            'dept_priority': [6, 7, 11, 18, 17, 2],
            'stages': {
                'all': {'id': 'all', 'name': 'Kapasitə (Ümumi)', 'count': 0, 'cap': 650, 'pct': 0},
                '0': {'id': '0', 'name': 'Satış (sifariş)', 'count': 0, 'cap': 200, 'pct': 0},
                '1': {'id': '1', 'name': 'Hörgü', 'count': 0, 'cap': 150, 'pct': 0},
                '4': {'id': '4', 'name': 'Forma', 'count': 0, 'cap': 150, 'pct': 0},
                '5': {'id': '5', 'name': 'Qablaşdırma', 'count': 0, 'cap': 150, 'pct': 0},
            },
            'stage_list_keys': ['all', '0', '1', '4', '5'],
            'color': 'acc',
            'bg': 'rgba(91,173,240,.05)'
        }

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────

def get_kpis(sector='corab'):
    rules = get_sector_rules(sector)
    cls_cond = rules['class_condition']
    """Header KPI cards — short cache to keep it mostly fresh without slowing down page loads."""
    sql = f"""
    SET NOCOUNT ON;

    -- Today's sales orders count
    SELECT COUNT(*) AS today_orders
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE {cls_cond}
      AND CAST(s.tarix AS DATE) = CAST(GETDATE() AS DATE);
    """
    today_orders = query_one(sql, cache_key=f'{sector}_kpi_today_orders', cache_ttl=60)

    sql2 = f"""
    SET NOCOUNT ON;
    SELECT
        SUM(e.mebleg) AS revenue_mtd,
        SUM(e.qaliq)  AS backlog_units,
        COUNT(DISTINCT s.kontra) AS active_customers
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE {cls_cond}
      AND s.tarix >= DATEADD(DAY, 1 - DAY(GETDATE()), CAST(GETDATE() AS DATE));
    """
    mtd = query_one(sql2, cache_key=f'{sector}_kpi_mtd', cache_ttl=60)

    sql3 = f"""
    SET NOCOUNT ON;
    SELECT COUNT(DISTINCT i.idn) AS active_prod_orders
    FROM sm_good_ist i WITH (NOLOCK)
    JOIN sm_good_ist_el e WITH (NOLOCK) ON e.es_no = i.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE {cls_cond}
      AND i.tarix >= DATEADD(DAY, -7, GETDATE())
      AND e.qaliq > 0;
    """
    prod = query_one(sql3, cache_key=f'{sector}_kpi_prod', cache_ttl=60)

    sql4 = f"""
    SET NOCOUNT ON;
    SELECT SUM(ms.miqdar) AS finished_stock
    FROM sm_mal_say ms WITH (NOLOCK)
    JOIN sm_goods g WITH (NOLOCK) ON ms.mal = g.idn
    WHERE {cls_cond}
      AND ms.anbar = 6
      AND ms.miqdar > 0;
    """
    stock = query_one(sql4, cache_key=f'{sector}_kpi_stock', cache_ttl=60)

    return {
        'today_orders': today_orders.get('today_orders', 0) if today_orders else 0,
        'revenue_mtd': round(mtd.get('revenue_mtd') or 0, 2) if mtd else 0,
        'backlog_units': int(mtd.get('backlog_units') or 0) if mtd else 0,
        'active_customers': mtd.get('active_customers', 0) if mtd else 0,
        'active_prod_orders': prod.get('active_prod_orders', 0) if prod else 0,
        'finished_stock': int(stock.get('finished_stock') or 0) if stock else 0,
    }


# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

def get_pipeline(sector='corab'):
    rules = get_sector_rules(sector)
    cls_cond = rules['class_condition']
    """Production stage pipeline — how many batches/shifts at each phase this month."""
    sql = f"""
    SET NOCOUNT ON;
    SELECT
        sm.faza,
        f.name AS faza_name,
        COUNT(*) AS shift_count,
        SUM(sm.mebleg) AS total_cost
    FROM sm_sobeler_med sm WITH (NOLOCK)
    LEFT JOIN sm_faza f WITH (NOLOCK) ON sm.faza = f.idn
    WHERE sm.anbar = 17
      AND sm.tarix >= DATEADD(DAY, 1 - DAY(GETDATE()), CAST(GETDATE() AS DATE))
    GROUP BY sm.faza, f.name
    ORDER BY sm.faza;
    """
    phases = query(sql, cache_key='pipeline', cache_ttl=120)

    # Also get raw materials warehouse stock
    sql2 = f"""
    SET NOCOUNT ON;
    SELECT SUM(ms.miqdar) AS raw_stock
    FROM sm_mal_say ms WITH (NOLOCK)
    JOIN sm_goods g WITH (NOLOCK) ON ms.mal = g.idn
    WHERE {cls_cond} AND ms.anbar = 2 AND ms.miqdar > 0;
    """
    raw = query_one(sql2, cache_key=f'{sector}_raw_stock', cache_ttl=120)

    # Finished goods
    sql3 = f"""
    SET NOCOUNT ON;
    SELECT SUM(ms.miqdar) AS fg_stock
    FROM sm_mal_say ms WITH (NOLOCK)
    JOIN sm_goods g WITH (NOLOCK) ON ms.mal = g.idn
    WHERE {cls_cond} AND ms.anbar = 6 AND ms.miqdar > 0;
    """
    fg = query_one(sql3, cache_key=f'{sector}_fg_stock', cache_ttl=120)

    return {
        'phases': phases,
        'raw_stock': int(raw.get('raw_stock') or 0) if raw else 0,
        'fg_stock': int(fg.get('fg_stock') or 0) if fg else 0,
    }


# ─────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────

def get_order_stage_map(sector='isci'):
    """
    STRICT ORDER ID TRACKING
    
    For Isci/Underwear: Uses sm_sob_trans (kesim -> tikis -> hazir)
    For Corab: Uses sm_good_ist (horgu=1, forma=4, hazir=5)
    """
    if sector == 'corab':
        sql = """
        SET NOCOUNT ON;
        SELECT
            i.sif_no AS order_id,
            SUM(CASE WHEN e.son_faza = 1 THEN e.miqdar ELSE 0 END) AS horgu_qty,
            SUM(CASE WHEN e.son_faza = 4 THEN e.miqdar ELSE 0 END) AS forma_qty,
            SUM(CASE WHEN e.son_faza = 5 THEN e.miqdar ELSE 0 END) AS hazir_qty
        FROM sm_good_ist i WITH (NOLOCK)
        JOIN sm_good_ist_el e WITH (NOLOCK) ON e.es_no = i.idn
        JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
        WHERE i.sif_no IS NOT NULL AND i.sif_no > 0
          AND g.class IN (21, 29, 30)
        GROUP BY i.sif_no
        """
        rows = query(sql, cache_key='corab_order_stage_map', cache_ttl=120)
        
        stage_map = {}
        for r in rows:
            oid = str(int(r['order_id']))
            hq = float(r['horgu_qty'] or 0)
            fq = float(r['forma_qty'] or 0)
            hq_fin = float(r['hazir_qty'] or 0)
            
            if hq_fin > 0:
                stage = 'hazir'
            elif fq > 0:
                stage = 'forma'
            elif hq > 0:
                stage = 'horgu'
            else:
                stage = 'none'
                
            stage_map[oid] = {
                'horgu_qty': hq,
                'forma_qty': fq,
                'hazir_qty': hq_fin,
                'stage': stage,
                # Compatibility properties for get_orders general variables if needed
                'sent_to_tikis': 0,
                'sent_to_hazir': 0,
                'in_tikis': 0,
                'kesim_events': 0
            }
        return stage_map
        
    else:
        # ISCI / UNDERWEAR logic
        sql = """
        SET NOCOUNT ON;
        SELECT
            t.el_sif AS order_id,
            SUM(CASE WHEN t.sobe2 IN (3,24) THEN 1 ELSE 0 END) AS kesim_events,
            SUM(CASE WHEN t.sobe1 IN (3,24)   AND t.sobe2 IN (4,5,39) THEN tel.miqdar ELSE 0 END) AS sent_to_tikis,
            SUM(CASE WHEN t.sobe1 IN (4,5,39) AND t.sobe2 IN (6,15)   THEN tel.miqdar ELSE 0 END) AS sent_to_hazir
        FROM sm_sob_trans t WITH (NOLOCK)
        JOIN sm_sob_trans_el tel WITH (NOLOCK) ON t.idn = tel.es_no
        WHERE t.tesdiq = 1
          AND t.el_sif IS NOT NULL
          AND (
                t.sobe2 IN (3,24)
             OR (t.sobe1 IN (3,24)   AND t.sobe2 IN (4,5,39))
             OR (t.sobe1 IN (4,5,39) AND t.sobe2 IN (6,15))
          )
        GROUP BY t.el_sif
        """
        rows = query(sql, cache_key='order_stage_map', cache_ttl=120)
        
        stage_map = {}
        for r in rows:
            oid = str(int(r['order_id']))
            ke = int(r['kesim_events'] or 0)
            s2t = float(r['sent_to_tikis'] or 0)
            s2h = float(r['sent_to_hazir'] or 0)
            in_tikis = max(0.0, s2t - s2h)
            
            # Determine dominant stage for the order
            if s2h > 0 and in_tikis == 0:
                stage = 'hazir'    # everything finished or in warehouse
            elif s2h > 0 and in_tikis > 0:
                stage = 'tikis'    # partially in tikis, partially in hazir
            elif in_tikis > 0:
                stage = 'tikis'    # cut pieces arrived at sewing, not yet finished
            elif ke > 0:
                stage = 'kesim'    # materials arrived at cutting, but nothing reached sewing yet
            else:
                stage = 'none'
                
            stage_map[oid] = {
                'kesim_events': ke,
                'sent_to_tikis': s2t,
                'sent_to_hazir': s2h,
                'in_tikis': in_tikis,
                'stage': stage,
                # Corab compat
                'horgu_qty': 0,
                'forma_qty': 0,
                'hazir_qty': 0
            }
        return stage_map

def get_orders(sector='corab'):
    from django.core.cache import cache
    cache_key = f"{sector}_orders_full_data"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    rules = get_sector_rules(sector)
    cls_cond = rules['class_condition']
    cls_cond_ym = rules['class_condition_ym']
    """FabriQ Order List — groups line items by customer and calculates stages/statuses."""
    # Step 1: Get all open orders. (Zero Data-Loss Logic for all sectors)
    sql = f"""
    SET NOCOUNT ON;
    SELECT
        s.idn AS order_id,
        s.sen_no,
        s.tam_yek AS order_total,
        CONVERT(VARCHAR(10), s.tarix, 23) AS tarix,
        s.kontra AS company_id,
        s.kontra_name AS company_name,
        e.idn AS line_id,
        e.num AS line_num,
        g.idn AS product_id,
        g.name AS product_name,
        e.miqdar AS qty_ordered,
        0 AS qty_remaining
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE {cls_cond}
      AND s.sif_sen IS NULL AND s.sif_form IS NULL
      AND s.tarix >= DATEADD(MONTH, -3, GETDATE())
      
    UNION ALL
    
    SELECT
        s.idn AS order_id,
        s.sen_no,
        s.yekun AS order_total,
        CONVERT(VARCHAR(10), s.tarix, 23) AS tarix,
        s.kontra AS company_id,
        c.name AS company_name,
        e.idn AS line_id,
        e.num AS line_num,
        g.idn AS product_id,
        g.name AS product_name,
        e.miqdar AS qty_ordered,
        e.miqdar AS qty_remaining
    FROM sm_sifaris_form s WITH (NOLOCK)
    JOIN sm_sifaris_form_el e WITH (NOLOCK) ON e.es_no = s.idn
    LEFT JOIN sm_kontra c WITH (NOLOCK) ON s.kontra = c.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE {cls_cond}
      AND s.tarix >= DATEADD(MONTH, -3, GETDATE())
      
    UNION ALL
    
    SELECT
        s.idn AS order_id,
        s.sen_no,
        s.yekun AS order_total,
        CONVERT(VARCHAR(10), s.tarix, 23) AS tarix,
        s.kontra AS company_id,
        c.name AS company_name,
        e.idn AS line_id,
        e.num AS line_num,
        g.idn AS product_id,
        g.name AS product_name,
        e.miqdar AS qty_ordered,
        (e.miqdar - ISNULL(e.sat_miq, 0)) AS qty_remaining
    FROM sm_sif_sened s WITH (NOLOCK)
    JOIN sm_sif_sened_el e WITH (NOLOCK) ON e.es_no = s.idn
    LEFT JOIN sm_kontra c WITH (NOLOCK) ON s.kontra = c.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE {cls_cond}
      AND s.tarix >= DATEADD(MONTH, -3, GETDATE())
      
    ORDER BY tarix ASC, line_num;  -- ASC order for FIFO allocation
    """
    base_lines = query(sql, cache_key=f'{sector}_fabriq_orders_lines_fifo', cache_ttl=120)

    # ─────────────────────────────────────────────────────────────────────
    # NEW: Fetch the Order Stage Map (single SQL, strict Order ID tracking)
    # ─────────────────────────────────────────────────────────────────────
    order_stage_map = {}
    try:
        order_stage_map = get_order_stage_map(sector)
    except Exception as e:
        print(f"Order stage map fetch failed: {e}")

    # ─────────────────────────────────────────────────────────────────────
    # NEW LOGIC: Strict Order ID Tracking (replaces FIFO + comment matching)
    # Each order line gets its current stage from the stage_map, which is
    # built from actual factory transfers tagged with el_sif (Order ID).
    # ─────────────────────────────────────────────────────────────────────
    from collections import defaultdict
    import copy
    import re

    raw_lines = []
    for order in base_lines:
        qaliq = float(order['qty_remaining'] or 0)
        ordered = float(order['qty_ordered'] or 0)
        delivered = ordered - qaliq

        # Sub-row for delivered portion (already shipped to customer)
        if delivered > 0:
            o_deliv = copy.deepcopy(order)
            o_deliv['qty_remaining'] = 0
            o_deliv['split_display'] = f"{int(delivered)}/{int(ordered)} (Tehvil verilib)"
            o_deliv['current_phase'] = 6  # Hazir
            raw_lines.append(o_deliv)

        if qaliq == 0:
            continue

        # Attach the stage from the transfer map (will be read later in the loop)
        o_split = copy.deepcopy(order)
        o_split['qty_remaining'] = qaliq
        o_split['split_display'] = ''
        o_split['current_phase'] = 0   # will be overridden below
        o_split['match_type'] = 'order_id'
        raw_lines.append(o_split)

    # Re-sort: latest order date first, grouped by company
    raw_lines.sort(key=lambda x: (x['company_name'] or '', x['tarix']), reverse=True)

    companies = {}
    import copy
    stages = copy.deepcopy(rules['stages'])

    # Fetch Customer Overall Debt
    sql_cust_balance = """
    SET NOCOUNT ON;
    SELECT kontra, SUM(yekun) as total_debt
    FROM sm_borc WITH (NOLOCK)
    GROUP BY kontra
    """
    cust_balances_raw = query(sql_cust_balance, cache_key='customer_balances', cache_ttl=300)
    cust_balances = {str(row['kontra']).strip(): float(row['total_debt'] or 0) for row in cust_balances_raw}

    # Fetch Customer Total Ordered
    sql_cust_orders = """
    SET NOCOUNT ON;
    SELECT kontra, SUM(tam_yek) as total_ordered
    FROM sm_kontr_sat WITH (NOLOCK)
    GROUP BY kontra
    """
    cust_orders_raw = query(sql_cust_orders, cache_key='customer_orders_total', cache_ttl=300)
    cust_orders = {str(row['kontra']).strip(): float(row['total_ordered'] or 0) for row in cust_orders_raw}

    # Fetch Order Payments
    sql_order_payments = """
    SET NOCOUNT ON;
    SELECT qaime, SUM(odenen) as total_paid
    FROM (
        SELECT qaime, odenen FROM sm_bank_od_el_el WITH (NOLOCK)
        UNION ALL
        SELECT qaime, odenen FROM sm_kmd_el WITH (NOLOCK)
    ) as p
    GROUP BY qaime
    """
    order_payments_raw = query(sql_order_payments, cache_key='order_payments', cache_ttl=300)
    order_payments = {row['qaime']: float(row['total_paid'] or 0) for row in order_payments_raw}
    stages = copy.deepcopy(rules['stages'])

    import hashlib

    def get_color(name):
        colors = [
            ('#a5b4fc', 'rgba(129,140,248,.18)'),
            ('#5ddba8', 'rgba(93,219,168,.18)'),
            ('#f5c842', 'rgba(245,200,66,.18)'),
            ('#f06b6b', 'rgba(240,107,107,.18)'),
            ('#c4b0ff', 'rgba(196,176,255,.18)'),
            ('#5badf0', 'rgba(91,173,240,.18)')
        ]
        idx = int(hashlib.md5(name.encode('utf-8')).hexdigest(), 16) % len(colors)
        return colors[idx]

    queue_estimates = {}
    material_readiness = {}
    if sector == 'isci':
        try:
            queue_estimates = calculate_active_queue_dates()
        except Exception as e:
            print(f"Queue estimation failed: {e}")
            
        try:
            from .material_checker import get_material_readiness
            # Use base_lines for true FIFO order quantities without splits
            material_readiness = get_material_readiness(base_lines) if 'base_lines' in locals() else {}
        except Exception as e:
            print(f"Material readiness failed: {e}")
            material_readiness = {}
            

    for row in raw_lines:
        etap_step = 0
        cid = row['company_id']
        cname = row['company_name'] or 'Bilinməyən'
        if cid not in companies:
            c, bg = get_color(cname)
            str_cid = str(cid).strip()
            t_debt = cust_balances.get(str_cid, 0)
            t_ordered = cust_orders.get(str_cid, 0)
            t_paid = t_ordered - t_debt
            companies[cid] = {
                'id': cid,
                'name': cname,
                'short': ''.join([w[0].upper() for w in cname.split() if w][:2]),
                'bg': bg,
                'c': c,
                'total_debt': t_debt,
                'total_ordered': t_ordered,
                'total_paid': t_paid,
                'orders': [],
                'stats': {'total': 0, 'late': 0, 'done': 0, 'active': 0, 'wait': 0}
            }
        
        qaliq = float(row['qty_remaining'] or 0)

        # ──────────────────────────────────────────────────────────────
        # STRICT ORDER ID STAGE DETECTION
        # Look up this order's current stage from the transfer map.
        # The map was built from sm_sob_trans with el_sif = order_id.
        # ──────────────────────────────────────────────────────────────
        order_id_str = str(int(row['order_id']))
        stage_info = order_stage_map.get(order_id_str, {})
        detected_stage = stage_info.get('stage', 'none')  # 'kesim', 'tikis', 'hazir', 'none'
        s2t = stage_info.get('sent_to_tikis', 0)
        s2h = stage_info.get('sent_to_hazir', 0)
        in_tikis = stage_info.get('in_tikis', 0)

        # Material readiness
        line_id = row.get('line_id')
        mat_info = material_readiness.get(line_id, {})
        readiness_pct = mat_info.get('readiness', 100) if qaliq > 0 else 100
        all_mats = mat_info.get('materials', [])
        is_material_ready = (readiness_pct == 100)

        is_late = False

        # Status based on detected stage
        if qaliq == 0:
            status = 'Tamamlandi'
            companies[cid]['stats']['done'] += 1
        elif detected_stage in ('kesim', 'tikis', 'hazir', 'horgu', 'forma'):
            status = 'Davam edir'
            companies[cid]['stats']['active'] += 1
        elif is_late:
            status = 'Gecikhmis'
            companies[cid]['stats']['late'] += 1
        else:
            status = 'Gozleyir'
            companies[cid]['stats']['wait'] += 1

        companies[cid]['stats']['total'] += 1

        # Map detected_stage to dashboard stage_key
        if sector == 'corab':
            if qaliq == 0:
                stage_key = '5'
            elif detected_stage == 'hazir':
                stage_key = '5'
            elif detected_stage == 'forma':
                stage_key = '4'
            elif detected_stage == 'horgu':
                stage_key = '1'
            else:
                stage_key = '0'
        else:
            # Isci Geyimi stages: 0=Satis, 1=Material, 2=Kesim, 3=Tikis, 4=Hazir
            if qaliq == 0:
                stage_key = '4'   # Delivered = complete
            elif detected_stage == 'hazir':
                stage_key = '4'   # In finished goods warehouse
            elif detected_stage == 'tikis':
                stage_key = '3'   # In sewing department
            elif detected_stage == 'kesim':
                stage_key = '2'   # Cutting started
            else:
                # No transfers found for this order_id
                if readiness_pct > 0:
                    stage_key = '1'  # Materials exist
                else:
                    stage_key = '0'  # Pure sales order, not yet started

        etap_step = 0
        if stage_key in stages:
            try:
                valid_keys = [k for k in rules['stage_list_keys'] if k != 'all']
                etap_step = valid_keys.index(stage_key)
            except ValueError:
                etap_step = 0
            stages[stage_key]['count'] += 1
            stages['all']['count'] += 1
            
        phase_display = stages.get(stage_key, {}).get('name', 'Satış (sifariş)')
        
        # Format the date properly for UI
        formatted_date = row['tarix']
        if isinstance(formatted_date, str) and len(formatted_date) >= 10:
            month_names = {'01':'Yan', '02':'Fev', '03':'Mar', '04':'Apr', '05':'May', '06':'İyun', '07':'İyul', '08':'Avq', '09':'Sen', '10':'Okt', '11':'Noy', '12':'Dek'}
            parts = formatted_date[:10].split('-')
            if len(parts) == 3:
                formatted_date = f"{int(parts[2])} {month_names.get(parts[1], parts[1])}"

        split_text = row.get('split_display', '')
        # If it's a split order, miqdar will be e.g. "60/100". Otherwise just "100".
        miqdar_val = split_text if split_text else str(int(float(row['qty_ordered'] or 0)))
        
        unique_id = f"{row['sen_no']}-{row['line_id']}"
        estimated_date = queue_estimates.get(unique_id, None) if 'queue_estimates' in locals() else None
        
        # Progress bar percentages (from the order stage map, keyed by order_id)
        total_ordered_qty = float(row['qty_ordered'] or 1)  # prevent div/0
        if sector == 'corab':
            pct_kesim = min(100, int((stage_info.get('horgu_qty', 0) / total_ordered_qty) * 100))
            pct_tikis = min(100, int((stage_info.get('forma_qty', 0) / total_ordered_qty) * 100))
            pct_hazir = min(100, int((stage_info.get('hazir_qty', 0) / total_ordered_qty) * 100))
            is_material_ready = (pct_kesim > 0)
            readiness_pct = pct_kesim if pct_kesim > 0 else 0
        else:
            pct_kesim  = min(100, int((s2t / total_ordered_qty) * 100))
            pct_tikis  = min(100, int((s2h / total_ordered_qty) * 100))

        # Material: if cutting started at all, materials must have been ready
        if pct_kesim > 0:
            pct_material = 100
        else:
            pct_material = readiness_pct

        # Payment data mapping
        o_id = row['order_id']
        o_total = float(row.get('order_total') or 0)
        o_paid = order_payments.get(o_id, 0)
        o_rem = o_total - o_paid
        if o_rem < 0: o_rem = 0

        companies[cid]['orders'].append({
            'id': unique_id,
            'cesid': row['product_name'],
            'miqdar': miqdar_val,
            'etapIdx': etap_step,
            'stage_id': str(stage_key),
            'phase_name': phase_display,
            'status': status,
            'tarix': formatted_date,
            'raw_tarix': row['tarix'],
            'estimated_delivery_date': estimated_date,
            'material_ready': is_material_ready,
            'material_readiness_pct': pct_material,
            'kesim_pct': pct_kesim,
            'tikis_pct': pct_tikis,
            'materials': all_mats,
            'materials_json': json.dumps(all_mats),
            'reng': get_color(row['product_name'])[0],
            'notes': 'Sistemden yuklendi',
            'order_id': row['order_id'],
            'order_total': o_total,
            'order_paid': o_paid,
            'order_remaining': o_rem,
            'sector_name': 'Isci geyimi' if sector == 'isci' else ('Corab' if sector == 'corab' else 'Underwear')
        })


    # Calculate percentages for stages
    for key, stage in stages.items():
        if key == 'all':
            total_cap = sum(s['cap'] for k, s in stages.items() if k != 'all')
            stage['cap'] = total_cap
        pct = min(round((stage['count'] / stage['cap']) * 100), 100) if stage['cap'] > 0 else 0
        stage['pct'] = pct

    company_list = list(companies.values())
    company_list.sort(key=lambda x: x['name'])
    
    stage_list = [stages[k] for k in rules['stage_list_keys']]
    
    # ---------------------------------------------
    # NEW LOGIC: Fetch Standard Productions
    # ---------------------------------------------
    standard_productions = []
    
    if sector != 'isci':
        sql_std = f"""
        SET NOCOUNT ON;
        SELECT TOP 300
            i.idn AS ist_id,
            CONVERT(VARCHAR(10), i.tarix, 23) AS tarix,
            g.idn AS product_id,
            g.name AS product_name,
            e.miqdar AS qty_produced,
            COALESCE(e.son_faza, 0) AS current_phase,
            COALESCE(f.name, '') AS phase_name
        FROM sm_good_ist i WITH (NOLOCK)
        JOIN sm_good_ist_el e WITH (NOLOCK) ON e.es_no = i.idn
        JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
        LEFT JOIN sm_faza f WITH (NOLOCK) ON e.son_faza = f.idn
        WHERE {cls_cond} AND (i.sif_no IS NULL OR i.sif_no = 0)
        ORDER BY i.tarix DESC
        """
        std_raw = query(sql_std, cache_key=f'{sector}_standard_prod', cache_ttl=120)
        
        for row in std_raw:
            phase = int(row['current_phase'] or 0)
            # map stage for standard
            if sector == 'corab':
                if phase == 1: stage_key = '1'
                elif phase in (4, 5): stage_key = '4'
                else: stage_key = '5' # Default to completed if standard prod
            else:
                if phase in (2, 8, 9): stage_key = '1'
                elif phase in (3, 24): stage_key = '2'
                elif phase in (4, 5, 39): stage_key = '3'
                elif phase in (6, 15): stage_key = '4'
                else: stage_key = '4' # Default to completed if unknown phase in standard prod
                
            phase_display = stages.get(stage_key, {}).get('name', 'Bilinmir')
            
            etap_step = 0
            if stage_key in stages:
                try:
                    valid_keys = [k for k in rules['stage_list_keys'] if k != 'all']
                    etap_step = valid_keys.index(stage_key)
                except ValueError:
                    etap_step = 0
                    
            standard_productions.append({
                'id': row['ist_id'],
                'cesid': row['product_name'],
                'miqdar': str(int(float(row['qty_produced'] or 0))),
                'stage_id': stage_key,
                'etapIdx': etap_step,
                'phase_name': phase_display,
                'tarix': row['tarix'],
                'status': 'Davam edir' if phase > 0 else 'Tamamlandı',
                'reng': get_color(row['product_name'])[0],
                'notes': 'Standart İstehsal',
                'sector_name': sector.capitalize()
            })
    # ---------------------------------------------
    
    result_data = {
        'companies': company_list,
        'stages': stage_list,
        'standard_productions': standard_productions
    }
    
    cache.set(cache_key, result_data, 120)
    return result_data


# ─────────────────────────────────────────────
# ORDER DETAIL
# ─────────────────────────────────────────────

def get_order_detail(order_id):
    """Full detail for one sales order: header + line items + production links."""
    # Header
    sql_header = f"""
    SET NOCOUNT ON;
    SELECT
        s.idn, s.sen_no,
        CONVERT(VARCHAR(10), s.tarix, 23) AS tarix,
        s.kontra_name,
        s.mebleg, s.tam_yek, s.guz_yek,
        CONVERT(VARCHAR(10), s.od_tar, 23) AS od_tar,
        s.serh
    FROM sm_kontr_sat s WITH (NOLOCK)
    WHERE s.idn = ?;
    """
    header = query_one(sql_header, params=(order_id,))

    # Line items
    sql_lines = f"""
    SET NOCOUNT ON;
    SELECT
        e.idn, e.num,
        g.name AS product_name,
        gc.name AS category,
        e.miqdar AS qty_ordered,
        e.qaliq AS qty_remaining,
        (e.miqdar - e.qaliq) AS qty_delivered,
        e.qiymet AS unit_price,
        e.mebleg AS line_total
    FROM sm_kontr_sat_el e WITH (NOLOCK)
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    LEFT JOIN sm_good_class gc WITH (NOLOCK) ON g.class = gc.idn
    WHERE e.es_no = ?
    ORDER BY e.num;
    """
    lines = query(sql_lines, params=(order_id,))

    # Production batches linked to this order
    sql_prod = f"""
    SET NOCOUNT ON;
    SELECT
        i.idn AS prod_id,
        i.sen_no AS prod_no,
        CONVERT(VARCHAR(10), i.tarix, 23) AS tarix,
        d1.name AS from_warehouse,
        d2.name AS to_warehouse,
        i.mebleg AS prod_cost,
        MAX(el.son_faza) AS current_phase,
        MAX(f.name) AS phase_name,
        SUM(el.miqdar) AS prod_qty
    FROM sm_good_ist i WITH (NOLOCK)
    JOIN sm_good_ist_el el WITH (NOLOCK) ON el.es_no = i.idn
    LEFT JOIN sm_depo d1 WITH (NOLOCK) ON i.anbar1 = d1.idn
    LEFT JOIN sm_depo d2 WITH (NOLOCK) ON i.anbar2 = d2.idn
    LEFT JOIN sm_faza f WITH (NOLOCK) ON el.son_faza = f.idn
    WHERE i.sif_no = ?
    GROUP BY i.idn, i.sen_no, i.tarix, d1.name, d2.name, i.mebleg
    ORDER BY i.tarix DESC;
    """
    productions = query(sql_prod, params=(order_id,))

    # Clean up numeric types
    for line in lines:
        for k in ('qty_ordered', 'qty_remaining', 'qty_delivered', 'unit_price', 'line_total'):
            line[k] = round(float(line.get(k) or 0), 2)
        total = float(line.get('qty_ordered') or 1)
        delivered = float(line.get('qty_delivered') or 0)
        line['pct'] = round(min(delivered / total * 100, 100), 1) if total > 0 else 0

    return {
        'header': header,
        'lines': lines,
        'productions': productions,
    }


# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────

def get_monthly_chart_data():
    """6-month trend: sales revenue + production units by category."""
    sql = f"""
    SET NOCOUNT ON;
    SELECT
        CONVERT(VARCHAR(7), s.tarix, 120) AS month,
        gc.name AS category,
        COUNT(DISTINCT s.idn) AS orders,
        SUM(e.miqdar) AS qty_sold,
        SUM(e.mebleg) AS revenue
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    JOIN sm_good_class gc WITH (NOLOCK) ON g.class = gc.idn
    WHERE g.class IN {SOCK_CLASSES}
      AND s.tarix >= DATEADD(MONTH, -6, GETDATE())
    GROUP BY CONVERT(VARCHAR(7), s.tarix, 120), gc.name
    ORDER BY month, gc.name;
    """
    sales = query(sql, cache_key='monthly_sales', cache_ttl=300)

    sql2 = f"""
    SET NOCOUNT ON;
    SELECT
        CONVERT(VARCHAR(7), i.tarix, 120) AS month,
        COUNT(DISTINCT i.idn) AS prod_runs,
        SUM(el.miqdar) AS qty_produced
    FROM sm_good_ist i WITH (NOLOCK)
    JOIN sm_good_ist_el el WITH (NOLOCK) ON el.es_no = i.idn
    JOIN sm_goods g WITH (NOLOCK) ON el.mal = g.idn
    WHERE g.class IN {SOCK_CLASSES}
      AND i.tarix >= DATEADD(MONTH, -6, GETDATE())
    GROUP BY CONVERT(VARCHAR(7), i.tarix, 120)
    ORDER BY month;
    """
    production = query(sql2, cache_key='monthly_prod', cache_ttl=300)

    return {'sales': sales, 'production': production}


def get_top_products(limit=10):
    """Top selling sock products last 60 days."""
    sql = f"""
    SET NOCOUNT ON;
    SELECT TOP {int(limit)}
        g.name AS product,
        gc.name AS category,
        SUM(e.miqdar) AS qty_sold,
        SUM(e.mebleg) AS revenue
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    JOIN sm_good_class gc WITH (NOLOCK) ON g.class = gc.idn
    WHERE g.class IN {SOCK_CLASSES}
      AND s.tarix >= DATEADD(DAY, -150, GETDATE())
    GROUP BY g.name, gc.name
    ORDER BY revenue DESC;
    """
    return query(sql, cache_key='top_products', cache_ttl=300)


def get_stock_by_warehouse():
    """Current socks stock per key warehouse."""
    sql = f"""
    SET NOCOUNT ON;
    SELECT
        d.name AS warehouse,
        ms.anbar,
        SUM(ms.miqdar) AS total_qty,
        COUNT(DISTINCT ms.mal) AS sku_count
    FROM sm_mal_say ms WITH (NOLOCK)
    JOIN sm_goods g WITH (NOLOCK) ON ms.mal = g.idn
    JOIN sm_depo d WITH (NOLOCK) ON ms.anbar = d.idn
    WHERE g.class IN {SOCK_CLASSES}
      AND ms.anbar IN {SOCK_WAREHOUSES}
      AND ms.miqdar > 0
    GROUP BY d.name, ms.anbar
    ORDER BY total_qty DESC;
    """
    return query(sql, cache_key='stock_warehouses', cache_ttl=300)


def get_todays_shifts(sector='corab'):
    rules = get_sector_rules(sector)
    cls = rules['classes']
    """Fetch all individual production shift/batch logs for today."""
    sql = f"""
    SET NOCOUNT ON;
    SELECT
        sm.idn,
        sm.sen_no,
        sm.faza,
        f.name AS faza_name,
        sm.mebleg AS cost,
        sm.ist_tap AS prod_order_id,
        CONVERT(VARCHAR(8), sm.bit_vaxt, 108) AS end_time,
        sm.ins_user AS operator
    FROM sm_sobeler_med sm WITH (NOLOCK)
    LEFT JOIN sm_faza f WITH (NOLOCK) ON sm.faza = f.idn
    WHERE sm.anbar IN (SELECT anbar FROM sm_good_ist_el WHERE mal IN (SELECT idn FROM sm_goods WHERE class IN {cls}))
      AND CAST(sm.tarix AS DATE) = CAST(GETDATE() AS DATE)
    ORDER BY sm.idn DESC;
    """
    return query(sql, cache_key=f'{sector}_todays_shifts', cache_ttl=60)


# ─────────────────────────────────────────────
# CAPACITY FORECASTING
# ─────────────────────────────────────────────

def get_capacity_forecast(sector='corab'):
    rules = get_sector_rules(sector)
    cls = rules['classes']
    """Calculate average production and backlog based on the last 60 days to forecast completion."""
    # 1. Total produced and active days in the last 60 days
    sql_prod = f"""
    SET NOCOUNT ON;
    SELECT 
        SUM(e.miqdar) as total_prod,
        COUNT(DISTINCT CAST(i.tarix AS DATE)) as active_days
    FROM sm_good_ist i WITH (NOLOCK)
    JOIN sm_good_ist_el e WITH (NOLOCK) ON i.idn = e.es_no
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE g.class IN {cls}
    AND i.tarix >= DATEADD(DAY, -150, GETDATE())
    """
    row_prod = query_one(sql_prod, cache_key=f'{sector}_prod_60d', cache_ttl=600)
    total_prod = float(row_prod['total_prod'] or 0)
    active_days = int(row_prod['active_days'] or 1)
    
    if active_days == 0: active_days = 1
    
    # The factory's true speed on days they actually work
    avg_per_active_day = int(round(total_prod / active_days)) if total_prod > 0 else 1
    
    # The frequency of working days (e.g. 23 days out of 60 = ~38% uptime)
    uptime_ratio = active_days / 60.0

    # 2. Total backlog from active orders (last 60 days)
    sql_backlog = f"""
    SET NOCOUNT ON;
    SELECT SUM(e.qaliq) as total_backlog
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON s.idn = e.es_no
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE g.class IN {cls}
    AND e.qaliq > 0
    AND s.tarix >= DATEADD(DAY, -150, GETDATE())
    """
    row_backlog = query_one(sql_backlog, cache_key=f'{sector}_backlog_60d', cache_ttl=600)
    total_backlog = float(row_backlog['total_backlog'] or 0)

    # Calculate how many ACTIVE working days are needed to clear the backlog
    working_days_to_clear = total_backlog / avg_per_active_day
    
    # We are deliberately NOT using the uptime_ratio here because the user wants
    # the date strictly mapped 1:1 against the active working day capacity.
    calendar_days_to_clear = int(round(working_days_to_clear))

    import datetime
    today = datetime.date.today()
    completion_date = today + datetime.timedelta(days=calendar_days_to_clear)
    
    # Format dates nicely in Azerbaijani
    months_az = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun", "İyul", "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"]
    comp_date_str = f"{completion_date.day} {months_az[completion_date.month - 1]}"

    return {
        'total_prod_60d': int(total_prod),
        'avg_per_day': avg_per_active_day,  # Show ~1060 to the user
        'uptime_ratio': uptime_ratio,       # Pass this to JS to scale new orders
        'total_backlog': int(total_backlog),
        'days_to_clear': calendar_days_to_clear,
        'completion_date_str': comp_date_str
    }
