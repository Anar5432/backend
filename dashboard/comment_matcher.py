import re
from .erp_connector import query

def fetch_commented_transfers():
    """Fetches recent transfers that have non-empty comments or notes."""
    sql = """
    SET NOCOUNT ON;
    SELECT 
        t.idn AS transfer_id,
        t.sen_no,
        t.tarix,
        t.sobe1,
        t.sobe2,
        t.serh AS comment,
        tel.qeyd AS note,
        tel.mal AS item_id,
        tel.miqdar AS qty,
        g.class AS item_class
    FROM sm_sob_trans t WITH (NOLOCK)
    JOIN sm_sob_trans_el tel WITH (NOLOCK) ON t.idn = tel.es_no
    JOIN sm_goods g WITH (NOLOCK) ON tel.mal = g.idn
    WHERE t.tarix >= DATEADD(DAY, -60, GETDATE())
      AND t.tesdiq = 1
      AND (
          (t.serh IS NOT NULL AND t.serh != '') OR 
          (tel.qeyd IS NOT NULL AND tel.qeyd != '')
      )
    ORDER BY t.tarix ASC;
    """
    return query(sql, cache_key='recent_comment_transfers', cache_ttl=120)

def match_orders_to_transfers(orders):
    """
    Takes a list of active orders (base_lines) and tries to match them to recent transfers
    based on fuzzy matching of company_name against transfer comments.
    Returns a dictionary mapping order_id -> list of matched transfers.
    """
    transfers = fetch_commented_transfers()
    
    # Pre-process order company names for fuzzy matching
    # e.g., 'TAMSTORE MMC' -> 'tamstore'
    order_map = {}
    for o in orders:
        cname = (o.get('company_name') or '').lower()
        # Clean up common suffixes
        cname = re.sub(r'\b(mmc|baki|azerbaycan|qapali sehmdar cemiyyeti|qsc|mms)\b', '', cname).strip()
        
        # Take the first main word if it's long, or the first two words
        words = cname.split()
        if words:
            # We'll use the first word as the primary matching key if it's > 3 chars
            key = words[0] if len(words[0]) > 3 else " ".join(words[:2])
            order_map[o['order_id']] = key
            
    matches = {}
    
    for t in transfers:
        comment = str(t.get('comment') or '').lower()
        note = str(t.get('note') or '').lower()
        combined_text = f"{comment} {note}"
        
        if not combined_text.strip():
            continue
            
        for order_id, search_key in order_map.items():
            if search_key and search_key in combined_text:
                if order_id not in matches:
                    matches[order_id] = []
                matches[order_id].append(t)
                
    return matches
