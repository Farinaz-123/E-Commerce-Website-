"""
Utility functions for the E-Commerce application
"""

def paginate_query(query, page, per_page=12):
    """
    Paginate a database query result
    
    Args:
        query: The database query result
        page: Current page number (1-indexed)
        per_page: Number of items per page
    
    Returns:
        tuple: (paginated_results, total_pages, current_page)
    """
    total_items = len(query)
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division
    
    # Validate page number
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    # Calculate start and end indices
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated = query[start_idx:end_idx]
    
    return paginated, total_pages, page


def get_avg_rating(product_id, conn):
    """Get average rating for a product"""
    result = conn.execute(
        "SELECT AVG(rating) as avg_rating FROM reviews WHERE product_id=?",
        (product_id,)
    ).fetchone()
    return result['avg_rating'] if result else 0


def validate_text(text, min_len=1, max_len=500):
    """Validate text input"""
    if not text or not isinstance(text, str):
        return False, "Invalid input"
    
    if len(text.strip()) < min_len:
        return False, f"Text must be at least {min_len} characters"
    
    if len(text.strip()) > max_len:
        return False, f"Text must be less than {max_len} characters"
    
    return True, "Valid"


def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal attacks"""
    import os
    filename = os.path.basename(filename)
    # Remove dangerous characters
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    return filename


def format_currency(amount):
    """Format amount as Indian Rupees"""
    return f"₹{amount:,.2f}"
