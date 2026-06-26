import sys
import copy
import re
from collections import defaultdict
from .erp_connector import query

COLORS = [
    'TÜND GÖY', 'AÇIQ BOZ', 'TÜND BOZ', 'AÇIQ MAVİ', 'TÜND QIRMIZI', 'AÇIQ YAŞIL', 'TÜND YAŞIL', 'SÜD RƏNGİ', 'TÜND QƏHVƏYİ', 'AÇIQ QƏHVƏYİ',
    'AĞ', 'QARA', 'BOZ', 'GÖY', 'QIRMIZI', 'LACİVƏRD', 'YAŞIL', 'SARI', 'ÇƏHRAYI', 'BEJ', 'XAKİ', 'MAVİ', 'BORDON', 'ANTRASİT', 'KREM', 'GÜMÜŞÜ', 'QIZILI', 'QƏHVƏYİ'
]

def extract_colors(name):
    name_upper = name.upper()
    found = set()
    for c in COLORS:
        if re.search(r'\b' + c + r'\b', name_upper):
            found.add(c)
    return found

def get_material_readiness(orders):
    """
    Computes material readiness for a list of orders using FIFO virtual reservation
    based on SMETA definitions and global inventory.
    
    `orders` should be a list of dictionaries containing:
      - line_id
      - product_id
      - product_name
      - qty_remaining
      - tarix
    
    Returns a dictionary mapping `line_id` to:
      {
         'readiness': int (0-100),
         'missing': [{'mat_name': str, 'needed': float, 'missing': float}, ...]
      }
    """
    if not orders:
        return {}

    # Sort orders by date for FIFO reservation (oldest first)
    # Ensure all orders have a tarix string for sorting
    sorted_orders = sorted(
        [o for o in orders if float(o.get('qty_remaining', 0)) > 0],
        key=lambda x: str(x.get('tarix', '9999-12-31'))
    )

    if not sorted_orders:
        return {}

    # 1. Fetch SMETA Requirements for all products in the orders
    product_ids = list(set([str(o['product_id']) for o in sorted_orders if o.get('product_id')]))
    if not product_ids:
        return {}
        
    product_colors = {}
    for o in sorted_orders:
        pid = str(o['product_id'])
        if pid not in product_colors:
            product_colors[pid] = extract_colors(o.get('product_name', ''))
            
    pid_str = ",".join(product_ids)
    
    sql_req = f"""
    SELECT 
        satis.mal AS hm_product_id,
        xammal.mal AS raw_material_id,
        MAX(g.name) AS raw_material_name,
        MAX(xammal.miqdar) AS qty_per_unit
    FROM sm_smeta_satis satis WITH (NOLOCK)
    JOIN (
        SELECT mal, MAX(es_no) as latest_smeta_id
        FROM sm_smeta_satis s WITH (NOLOCK)
        JOIN sm_smeta sm WITH (NOLOCK) ON s.es_no = sm.idn
        WHERE sm.tesdiq = 1 AND s.mal IN ({pid_str})
        GROUP BY mal
    ) latest ON satis.mal = latest.mal AND satis.es_no = latest.latest_smeta_id
    JOIN sm_smeta_xammal xammal WITH (NOLOCK) ON satis.es_no = xammal.es_no
    JOIN sm_goods g WITH (NOLOCK) ON xammal.mal = g.idn
    WHERE satis.mal IN ({pid_str})
    GROUP BY satis.mal, xammal.mal
    """
    
    try:
        import hashlib
        pid_hash = hashlib.md5(pid_str.encode()).hexdigest()
        req_raw = query(sql_req, cache_key=f'smeta_req_{pid_hash}', cache_ttl=300)
    except Exception as e:
        print(f"Error fetching SMETA: {e}")
        return {}

    smeta_reqs = defaultdict(list)
    all_needed_materials = set()
    for r in req_raw:
        hm_product_id = str(r['hm_product_id'])
        mat_name = r['raw_material_name']
        mat_colors = extract_colors(mat_name)
        p_colors = product_colors.get(hm_product_id, set())
        
        # Smart Filter: If product has color and material has color, and they don't intersect, ignore this material.
        if p_colors and mat_colors and not p_colors.intersection(mat_colors):
            continue
            
        smeta_reqs[hm_product_id].append({
            'mat_id': r['raw_material_id'],
            'mat_name': r['raw_material_name'],
            'qty_per_unit': float(r['qty_per_unit'])
        })
        all_needed_materials.add(r['raw_material_id'])

    # 2. Fetch Global Inventory for these specific materials
    global_inventory = defaultdict(float)
    if all_needed_materials:
        mat_list = ",".join(str(m) for m in all_needed_materials)
        sql_inv = f"""
        SELECT 
            dept_id, mal, SUM(balance) as balance
        FROM (
            SELECT 
                ISNULL(ins.dept_id, outs.dept_id) as dept_id,
                ISNULL(ins.mal, outs.mal) as mal,
                ISNULL(ins.qty_in, 0) - ISNULL(outs.qty_out, 0) as balance
            FROM (
                SELECT t.sobe2 AS dept_id, tel.mal, SUM(tel.miqdar) AS qty_in
                FROM sm_sob_trans t WITH (NOLOCK)
                JOIN sm_sob_trans_el tel WITH (NOLOCK) ON t.idn = tel.es_no
                WHERE t.tesdiq = 1 AND tel.mal IN ({mat_list}) AND t.sobe2 IS NOT NULL
                GROUP BY t.sobe2, tel.mal
            ) ins
            FULL OUTER JOIN (
                SELECT t.sobe1 AS dept_id, tel.mal, SUM(tel.miqdar) AS qty_out
                FROM sm_sob_trans t WITH (NOLOCK)
                JOIN sm_sob_trans_el tel WITH (NOLOCK) ON t.idn = tel.es_no
                WHERE t.tesdiq = 1 AND t.sobe1 IS NOT NULL AND tel.mal IN ({mat_list})
                GROUP BY t.sobe1, tel.mal
            ) outs ON ins.dept_id = outs.dept_id AND ins.mal = outs.mal
        ) bal
        WHERE balance > 0
        GROUP BY dept_id, mal
        """
        try:
            import hashlib
            mat_hash = hashlib.md5(mat_list.encode()).hexdigest()
            inventory_raw = query(sql_inv, cache_key=f'smeta_inv_{mat_hash}', cache_ttl=120)
            for row in inventory_raw:
                global_inventory[row['mal']] += float(row['balance'])
        except Exception as e:
            print(f"Error fetching inventory: {e}")

    # 3. Process FIFO Reservation
    virtual_inventory = copy.deepcopy(global_inventory)
    results = {}

    for o in sorted_orders:
        lid = o.get('line_id')
        if not lid: continue
            
        pid = str(o.get('product_id'))
        qaliq = float(o.get('qty_remaining', 0))
        
        if pid not in smeta_reqs:
            results[lid] = {
                'readiness': 0,
                'materials': []
            }
            continue

        reqs = smeta_reqs[pid]
        all_materials = []
        total_items = len(reqs)
        items_ready = 0
        
        for r in reqs:
            mat_id = r['mat_id']
            needed_qty = r['qty_per_unit'] * qaliq
            avail_qty = virtual_inventory.get(mat_id, 0)
            
            if avail_qty >= needed_qty:
                virtual_inventory[mat_id] -= needed_qty
                items_ready += 1
                all_materials.append({
                    'mat_name': r['mat_name'],
                    'needed': round(needed_qty, 2),
                    'available': round(avail_qty, 2),
                    'missing': 0,
                    'is_ready': True
                })
            else:
                missing_qty = needed_qty - avail_qty
                virtual_inventory[mat_id] = 0
                all_materials.append({
                    'mat_name': r['mat_name'],
                    'needed': round(needed_qty, 2),
                    'available': round(avail_qty, 2),
                    'missing': round(missing_qty, 2),
                    'is_ready': False
                })
        
        readiness_percentage = int((items_ready / total_items) * 100) if total_items > 0 else 0
        
        results[lid] = {
            'readiness': readiness_percentage,
            'materials': all_materials
        }

    return results
