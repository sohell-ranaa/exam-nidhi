"""
Y6 Practice Exam - Pagination Helper
Professional pagination for all lists
"""

from math import ceil
from typing import Dict, Any, List


class Paginator:
    """Professional pagination system"""

    def __init__(self, total_items: int, page: int = 1, per_page: int = 10):
        self.total_items = total_items
        self.per_page = min(max(per_page, 5), 100)  # Between 5-100
        self.page = max(page, 1)
        self.total_pages = ceil(total_items / self.per_page) if total_items > 0 else 1

        # Ensure page is within bounds
        if self.page > self.total_pages:
            self.page = self.total_pages

    @property
    def offset(self) -> int:
        """Get SQL OFFSET value"""
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        """Get SQL LIMIT value"""
        return self.per_page

    @property
    def has_prev(self) -> bool:
        """Check if previous page exists"""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """Check if next page exists"""
        return self.page < self.total_pages

    @property
    def prev_page(self) -> int:
        """Get previous page number"""
        return self.page - 1 if self.has_prev else None

    @property
    def next_page(self) -> int:
        """Get next page number"""
        return self.page + 1 if self.has_next else None

    @property
    def start_item(self) -> int:
        """First item number on current page"""
        return self.offset + 1 if self.total_items > 0 else 0

    @property
    def end_item(self) -> int:
        """Last item number on current page"""
        return min(self.offset + self.per_page, self.total_items)

    def page_range(self, window: int = 2) -> List[int]:
        """Get page numbers for pagination UI"""
        pages = []
        start = max(1, self.page - window)
        end = min(self.total_pages, self.page + window)

        for i in range(start, end + 1):
            pages.append(i)

        return pages

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for templates"""
        return {
            'page': self.page,
            'per_page': self.per_page,
            'total_items': self.total_items,
            'total_pages': self.total_pages,
            'has_prev': self.has_prev,
            'has_next': self.has_next,
            'prev_page': self.prev_page,
            'next_page': self.next_page,
            'start_item': self.start_item,
            'end_item': self.end_item,
            'page_range': self.page_range(),
        }


def paginate_query(cursor, query: str, count_query: str, params: tuple = (),
                   page: int = 1, per_page: int = 10) -> tuple:
    """
    Execute paginated query and return (items, pagination)

    Args:
        cursor: MySQL cursor
        query: SELECT query (without LIMIT/OFFSET)
        count_query: COUNT query for total items
        params: Query parameters
        page: Current page number
        per_page: Items per page

    Returns:
        Tuple of (items list, Paginator object)
    """
    # Get total count
    cursor.execute(count_query, params)
    result = cursor.fetchone()
    total = result['count'] if isinstance(result, dict) else result[0]

    # Create paginator
    paginator = Paginator(total, page, per_page)

    # Execute paginated query
    paginated_query = f"{query} LIMIT {paginator.limit} OFFSET {paginator.offset}"
    cursor.execute(paginated_query, params)
    items = cursor.fetchall()

    return items, paginator
