from datetime import datetime, timedelta
from .erp_connector import query
from django.core.cache import cache
from .throughput_engine import get_throughput_rates, extract_family

def add_working_days(start_date, working_days_to_add):
    """
    Adds working days to a given start date (skipping weekends).
    """
    current_date = start_date
    days_added = 0
    while days_added < int(working_days_to_add):
        current_date += timedelta(days=1)
        # Skip Saturday (5) and Sunday (6)
        if current_date.weekday() < 5:
            days_added += 1
    return current_date

def calculate_active_queue_dates():
    """
    Calculates the estimated completion date for every active order.
    Returns a dictionary: { 'order_id': estimated_end_date_string }
    """
    rates = get_throughput_rates()
    
    # Calculate a global fallback average speed if a product family is entirely unknown
    valid_speeds = [data['pieces_per_day'] for fam, data in rates.items() if data['pieces_per_day'] > 0]
    global_avg_speed = sum(valid_speeds) / len(valid_speeds) if valid_speeds else 10.0
    
    # Pull all active Workwear (class 27) orders that need to be produced (qaliq > 0)
    sql = """
    SELECT
        s.idn AS order_id,
        s.sen_no,
        s.tarix AS order_date,
        e.idn AS line_id,
        g.name AS product_name,
        g.muddet AS product_muddet,
        e.qaliq AS qty_remaining
    FROM sm_kontr_sat s WITH (NOLOCK)
    JOIN sm_kontr_sat_el e WITH (NOLOCK) ON e.es_no = s.idn
    JOIN sm_goods g WITH (NOLOCK) ON e.mal = g.idn
    WHERE g.class = 27 AND e.qaliq > 0
    ORDER BY s.tarix ASC, e.num ASC
    """
    try:
        active_orders = query(sql, cache_key='active_orders_queue_isci', cache_ttl=120)
    except Exception as e:
        print(f"Error fetching active orders for queue: {e}")
        return {}
    
    # Start simulating the queue from today
    # (In a true pipeline, all orders are stacked behind the single current bottleneck)
    queue_estimates = {}
    family_queues = {}
    
    # Pre-populate family queues starting from today/next monday
    start_date = datetime.now()
    if start_date.weekday() == 5:
        start_date += timedelta(days=2)
    elif start_date.weekday() == 6:
        start_date += timedelta(days=1)
    
    for o in active_orders:
        qaliq = float(o['qty_remaining'])
        if qaliq <= 0:
            continue
            
        fam = extract_family(o['product_name'])
        if fam not in family_queues:
            family_queues[fam] = start_date
            
        speed = global_avg_speed
        if fam in rates:
            speed = rates[fam]['pieces_per_day']
        elif o['product_muddet'] and float(o['product_muddet']) > 0:
            target_muddet = float(o['product_muddet'])
            closest_fam = min(rates.keys(), key=lambda k: abs(rates[k]['avg_muddet'] - target_muddet))
            speed = rates[closest_fam]['pieces_per_day']
            
        speed = max(speed, 0.1)
        working_days_needed = qaliq / speed
        
        # Advance the specific family pipeline date
        family_queues[fam] = add_working_days(family_queues[fam], working_days_needed)
        
        unique_id = f"{o['sen_no']}-{o['line_id']}"
        queue_estimates[unique_id] = family_queues[fam].strftime('%Y-%m-%d')
        
    # Store the family queues state globally so what-if can access it
    cache.set('workwear_family_queues_end', family_queues, 86400)
    return queue_estimates

def get_whatif_estimate(product_family, quantity, workers):
    # Ensure queues are calculated
    calculate_active_queue_dates()
    family_queues = cache.get('workwear_family_queues_end') or {}
    
    # Get the specific queue for this product family
    start_date = datetime.now()
    if start_date.weekday() == 5:
        start_date += timedelta(days=2)
    elif start_date.weekday() == 6:
        start_date += timedelta(days=1)
        
    factory_free_date = family_queues.get(product_family, start_date)
        
    rates = get_throughput_rates()
    base_speed = rates.get(product_family, {}).get('pieces_per_day', 10.0)
    
    # Assume the historical baseline speed was achieved with a "standard" number of workers
    # If standard workers is e.g., 20, and user enters 10, the speed is halved.
    # Without firm historical worker counts, we assume the baseline speed = baseline workers (e.g. 10)
    # The user enters how many workers they will dedicate.
    STANDARD_WORKERS = 10.0 
    
    if workers and float(workers) > 0:
        adjustment_factor = float(workers) / STANDARD_WORKERS
        adjusted_speed = base_speed * adjustment_factor
    else:
        adjusted_speed = base_speed
        
    adjusted_speed = max(adjusted_speed, 0.1)
    working_days_needed = float(quantity) / adjusted_speed
    
    estimated_delivery_date = add_working_days(factory_free_date, working_days_needed)
    
    return {
        'queue_ends': factory_free_date.strftime('%Y-%m-%d'),
        'working_days_needed': round(working_days_needed, 1),
        'adjusted_speed_per_day': round(adjusted_speed, 1),
        'estimated_delivery': estimated_delivery_date.strftime('%Y-%m-%d')
    }
