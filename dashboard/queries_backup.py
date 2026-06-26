"""
queries.py — All SQL queries for the Socks Dashboard.
Socks classes: 21 (CORAB), 29 (QADIN CORABI), 30 (UŞAQ CORABI)
Socks warehouses: 2 (Raw Mat), 6 (Finished Goods), 7 (Binə Store),
                  11 (Sədərək Store), 17 (Workshop), 18 (Staging)
"""
from .erp_connector import query, query_one
from .queue_engine import calculate_active_queue_dates

def get_sector_rules(sector):
    if sector == 'isci':
        return {
            'classes': '(27)',
            'warehouses': '(2, 6, 17, 18)', # Optional
            'stages': {
                'all': {'id': 'all', 'name': 'Kapasitə (Ümumi)', 'count': 0, 'cap': 700, 'pct': 0},
                '0': {'id': '0', 'name': 'Satış (sifariş)', 'count': 0, 'cap': 250, 'pct': 0},
                '1': {'id': '1', 'name': 'Anbar (Material)', 'count': 0, 'cap': 150, 'pct': 0},
                '2': {'id': '2', 'name': 'Kəsim', 'count': 0, 'cap': 150, 'pct': 0},
                '4': {'id': '4', 'name': 'Tikiş', 'count': 0, 'cap': 150, 'pct': 0},
                '5': {'id': '5', 'name': 'Anbar', 'count': 0, 'cap': 150, 'pct': 0},
            },
            'stage_list_keys': ['all', '0', '1', '2', '4', '5'],
            'color': 'grn',
            'bg': 'rgba(93,219,168,.05)'
        }
    else: # corab
        return {
            'classes': '(21, 29, 30)',
            'warehouses': '(2, 6, 7, 11, 17, 18)',
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
    cls = rules['classes']
    """Header KPI cards — always fresh (no cache), called on every page load."""
    sql = f"""
    SET NOCOUNT ON;

    -- Today's sales orders count
    SELECT COUNT(*) AS today_orders
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE g.class IN {cls}
      AND CAST(s.tarix AS DATE) = CAST(GETDATE() AS DATE);
    """
    today_orders = query_one(sql)

    sql2 = f"""
    SET NOCOUNT ON;
    SELECT
        SUM(e.mebleg) AS revenue_mtd,
        SUM(e.qaliq)  AS backlog_units,
        COUNT(DISTINCT s.kontra) AS active_customers
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE g.class IN {cls}
      AND s.tarix >= DATEADD(DAY, 1 - DAY(GETDATE()), CAST(GETDATE() AS DATE));
    """
    mtd = query_one(sql2)

    sql3 = f"""
    SET NOCOUNT ON;
    SELECT COUNT(DISTINCT i.idn) AS active_prod_orders
    FROM sm_good_ist i WITH (NOLOCK)
    JOIN sm_good_ist_el e WITH (NOLOCK) ON e.es_no = i.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE g.class IN {cls}
      AND i.tarix >= DATEADD(DAY, -7, GETDATE())
      AND e.qaliq > 0;
    """
    prod = query_one(sql3)

    sql4 = f"""
    SET NOCOUNT ON;
    SELECT SUM(ms.miqdar) AS finished_stock
    FROM sm_mal_say ms WITH (NOLOCK)
    JOIN sm_goods g WITH (NOLOCK) ON ms.mal = g.idn
    WHERE g.class IN {cls}
      AND ms.anbar = 6
      AND ms.miqdar > 0;
    """
    stock = query_one(sql4)

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
    cls = rules['classes']
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
    WHERE g.class IN {cls} AND ms.anbar = 2 AND ms.miqdar > 0;
    """
    raw = query_one(sql2, cache_key=f'{sector}_raw_stock', cache_ttl=120)

    # Finished goods
    sql3 = f"""
    SET NOCOUNT ON;
    SELECT SUM(ms.miqdar) AS fg_stock
    FROM sm_mal_say ms WITH (NOLOCK)
    JOIN sm_goods g WITH (NOLOCK) ON ms.mal = g.idn
    WHERE g.class IN {cls} AND ms.anbar = 6 AND ms.miqdar > 0;
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

def get_orders(sector='corab'):
    rules = get_sector_rules(sector)
    cls = rules['classes']
    """FabriQ Order List — groups line items by customer and calculates stages/statuses."""
    if sector == 'corab':
        sql = f"""
        SET NOCOUNT ON;
        SELECT
            s.idn AS order_id,
            s.sen_no,
            CONVERT(VARCHAR(10), s.tarix, 23) AS tarix,
            s.kontra AS company_id,
            s.kontra_name AS company_name,
            e.idn AS line_id,
            e.num AS line_num,
            g.name AS product_name,
            e.miqdar AS qty_ordered,
            e.qaliq AS qty_remaining,
            COALESCE(el.son_faza, 0) AS current_phase,
            COALESCE(f.name, '') AS phase_name
        FROM sm_kontr_sat s WITH (NOLOCK)
        JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
        JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
        LEFT JOIN (
            SELECT sif_no, MAX(idn) as last_ist
            FROM sm_good_ist WITH (NOLOCK)
            GROUP BY sif_no
        ) last_prod ON last_prod.sif_no = s.idn
        LEFT JOIN sm_good_ist_el el WITH (NOLOCK) ON el.es_no = last_prod.last_ist AND el.mal = e.mal
        LEFT JOIN sm_faza f WITH (NOLOCK) ON el.son_faza = f.idn
        WHERE g.class IN {cls}
          AND (e.qaliq > 0 OR s.tarix >= DATEADD(DAY, -60, GETDATE()))
        ORDER BY s.kontra_name, s.tarix DESC, e.num;
        """
        raw_lines = query(sql, cache_key=f'{sector}_fabriq_orders', cache_ttl=120)
    else:
        # Step 1: Get all open orders.
        sql = f"""
        SET NOCOUNT ON;
        SELECT
            s.idn AS order_id,
            s.sen_no,
            CONVERT(VARCHAR(10), s.tarix, 23) AS tarix,
            s.kontra AS company_id,
            s.kontra_name AS company_name,
            e.idn AS line_id,
            e.num AS line_num,
            g.idn AS product_id,
            g.name AS product_name,
            e.miqdar AS qty_ordered,
            e.qaliq AS qty_remaining
        FROM sm_kontr_sat s WITH (NOLOCK)
        JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
        JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
        WHERE g.class IN {cls}
          AND (e.qaliq > 0 OR s.tarix >= DATEADD(DAY, -60, GETDATE()))
        ORDER BY s.tarix ASC, e.num;  -- ASC order for FIFO allocation
        """
        base_lines = query(sql, cache_key=f'{sector}_fabriq_orders_lines_fifo', cache_ttl=120)

        # Step 2: Get balances for the corresponding YM- items
        sql_balances = f"""
        SELECT 
            hm_goods.idn AS hm_mal,
            dept.idn AS dept_id,
            ISNULL(ins.qty_in, 0) - ISNULL(outs.qty_out, 0) AS balance
        FROM sm_goods hm_goods WITH (NOLOCK)
        JOIN sm_goods ym_g WITH (NOLOCK) ON 
            ym_g.class IN {cls} AND (
                hm_goods.idn = ym_g.idn
                OR (ym_g.name LIKE 'YM-%' AND hm_goods.name LIKE 'HM-%'
                    AND SUBSTRING(ym_g.name, 4, LEN(ym_g.name)) = SUBSTRING(hm_goods.name, 4, LEN(hm_goods.name)))
            )
        JOIN (
            SELECT t.sobe2 AS dept_id, tel.mal, SUM(tel.miqdar) AS qty_in
            FROM sm_sob_trans t WITH (NOLOCK)
            JOIN sm_sob_trans_el tel WITH (NOLOCK) ON t.idn = tel.es_no
            WHERE t.tesdiq = 1
            GROUP BY t.sobe2, tel.mal
        ) ins ON ym_g.idn = ins.mal
        LEFT JOIN sm_depo dept WITH (NOLOCK) ON ins.dept_id = dept.idn
        LEFT JOIN (
            SELECT t.sobe1 AS dept_id, tel.mal, SUM(tel.miqdar) AS qty_out
            FROM sm_sob_trans t WITH (NOLOCK)
            JOIN sm_sob_trans_el tel WITH (NOLOCK) ON t.idn = tel.es_no
            WHERE t.tesdiq = 1 AND t.sobe1 IS NOT NULL
            GROUP BY t.sobe1, tel.mal
        ) outs ON ins.dept_id = outs.dept_id AND ins.mal = outs.mal
        WHERE hm_goods.class IN {cls}
          AND (ISNULL(ins.qty_in, 0) - ISNULL(outs.qty_out, 0)) > 0
        """
        balances_raw = query(sql_balances, cache_key=f'{sector}_fabriq_balances', cache_ttl=120)
        
        from collections import defaultdict
        import copy
        
        product_balances = defaultdict(lambda: defaultdict(float))
        for b in balances_raw:
            product_balances[b['hm_mal']][b['dept_id']] += float(b['balance'])
            
        raw_lines = []
        for order in base_lines:
            qaliq = float(order['qty_remaining'] or 0)
            ordered = float(order['qty_ordered'] or 0)
            delivered = ordered - qaliq
            
            # Sub-row for delivered portion
            if delivered > 0:
                o_deliv = copy.deepcopy(order)
                o_deliv['qty_remaining'] = 0  # acts as Tamamlandı
                o_deliv['split_display'] = f"{int(delivered)}/{int(ordered)}"
                o_deliv['current_phase'] = 6
                raw_lines.append(o_deliv)
                
            if qaliq == 0:
                continue
                
            hm_mal = order['product_id']
            bals = product_balances[hm_mal]
            
            # Priority order of departments to pull from (closest to finish first)
            dept_priority = [6, 15, 39, 5, 4, 3, 24, 8, 9]
            remaining_to_find = qaliq
            
            for dept_id in dept_priority:
                if remaining_to_find <= 0:
                    break
                available = bals[dept_id]
                if available > 0:
                    take = min(available, remaining_to_find)
                    bals[dept_id] -= take
                    remaining_to_find -= take
                    
                    o_split = copy.deepcopy(order)
                    o_split['qty_remaining'] = qaliq # keeps it active
                    o_split['split_display'] = f"{int(take)}/{int(ordered)}"
                    o_split['current_phase'] = dept_id
                    raw_lines.append(o_split)
                    
            if remaining_to_find > 0:
                o_split = copy.deepcopy(order)
                o_split['qty_remaining'] = qaliq
                o_split['split_display'] = f"{int(remaining_to_find)}/{int(ordered)}" if remaining_to_find < ordered else ""
                o_split['current_phase'] = 0
                raw_lines.append(o_split)
                
        # Re-sort for display (latest first)
        raw_lines.sort(key=lambda x: (x['company_name'] or '', x['tarix']), reverse=True)

    companies = {}
    import copy
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
            order_ids = list(set([r['order_id'] for r in raw_lines]))
            from .material_checker import get_material_readiness
            material_readiness = get_material_readiness(order_ids)
        except Exception as e:
            print(f"Material readiness failed: {e}")

    for row in raw_lines:
        cid = row['company_id']
        cname = row['company_name'] or 'Bilinməyən'
        if cid not in companies:
            c, bg = get_color(cname)
            companies[cid] = {
                'id': cid,
                'name': cname,
                'short': ''.join([w[0].upper() for w in cname.split() if w][:2]),
                'bg': bg,
                'c': c,
                'orders': [],
                'stats': {'total': 0, 'late': 0, 'done': 0, 'active': 0, 'wait': 0}
            }
        
        qaliq = float(row['qty_remaining'] or 0)
        phase = int(row['current_phase'] or 0)
        is_material_ready = material_readiness.get(row['order_id'], True)
        
        is_late = False 
        
        if qaliq == 0:
            status = 'Tamamlandı'
            companies[cid]['stats']['done'] += 1
        elif phase > 0:
            status = 'Davam edir'
            companies[cid]['stats']['active'] += 1
        elif is_late:
            status = 'Gecikmiş'
            companies[cid]['stats']['late'] += 1
        else:
            status = 'Gözləyir'
            companies[cid]['stats']['wait'] += 1
            
        companies[cid]['stats']['total'] += 1
        
        phase_str = str(phase)
        if sector == 'corab':
            if qaliq == 0:
                stage_key = '5'
            elif phase == 1:
                stage_key = '1'
            elif phase in (4, 5):
                stage_key = '4'
            else:
                stage_key = '0'
        else:
            # İşçi Geyimi mapping using CURRENT department (phase = dept_id = sobe2)
            # phase tells us WHERE the item is CURRENTLY located:
            #   0  => no production started => Satış (stage 0)
            #   2, 8, 9 => Material warehouse => Anbar (Material) (stage 1)
            #   3, 24 => Kəsim/Experimental => Kəsim (stage 2)
            #   4, 5, 39 => Tikiş/Mayka/Son Bölüm => Tikiş (stage 4)
            #   6, 15 => Hazır Məhsul / Internal Sales => Anbar (stage 5)
            
            if qaliq == 0:
                stage_key = '5'  # Qaliq is 0, item is fully delivered = completed
            elif phase == 0:
                stage_key = '0'  # No transfer at all = Satış
            elif phase in (2, 8, 9):
                stage_key = '1'  # Material anbarında
            elif phase in (3, 24):
                stage_key = '2'  # Kəsimdə
            elif phase in (4, 5, 39):
                stage_key = '4'  # Tikişdə
            elif phase in (6, 15):
                stage_key = '5'  # Hazır Məhsul Anbarında
            else:
                stage_key = '0'  # Unknown = Satış

        if stage_key in stages:
            try:
                etap_step = rules['stage_list_keys'].index(stage_key) - 1
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
        
        unique_id = f"{row['sen_no']}-{row['line_num']}"
        estimated_date = queue_estimates.get(unique_id, None) if 'queue_estimates' in locals() else None
        
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
            'reng': get_color(row['product_name'])[0],
            'notes': 'Sistemdən yükləndi',
            'order_id': row['order_id'],
            'sector_name': 'İşçi geyimi' if sector == 'isci' else 'Corab'
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
    
    return {
        'companies': company_list,
        'stages': stage_list
    }


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
      AND s.tarix >= DATEADD(DAY, -60, GETDATE())
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
    AND i.tarix >= DATEADD(DAY, -60, GETDATE())
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
    AND s.tarix >= DATEADD(DAY, -60, GETDATE())
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
