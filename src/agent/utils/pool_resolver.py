def normalize_pool_name(pool_name):
    """
    Normalize pool name and use default if not specified.
    """
    if not pool_name or pool_name.lower() in ["both", "both pools", "all", "all pools"]:
        return "Both Pools"
    
    if pool_name.lower() in ["indoor", "indoor pool"]:
        return "Indoor Pool"
    
    if pool_name.lower() in ["outdoor", "outdoor pool"]:
        return "Outdoor Pool"
    
    # If it's something else, return as is
    return pool_name