from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc, case
from pydantic import BaseModel

from models import Product, ProductPriceHistory, SearchHistory, UserRecommendation
from dependencies.deps import get_db, get_current_user, get_optional_current_user
from fastapi.security import OAuth2PasswordBearer

# ----------------------------------------
# 1) Define your accessories search dict
# ----------------------------------------
accessories_search_keywords = {
    "protection": [
        "كفر", "cover", "case", "واقي شاشة", "screen protector", "tempered glass",
        "protector", "protection", "حافظة", "antishock", "portector", "حماية",
        "shield", "rotatable", "for iphone"
    ],
    "charging": [
        "شاحن", "charger", "كيبل", "كابل", "cable", "power bank", "بنك طاقة",
        "شاحن سيارة", "car charger", "magsafe", "شاحن لاسلكي", "wireless charger"
    ],
    "audio": [
        "سماعة", "سماعات", "earbuds", "earphones", "headset",
        "سماعة بلوتوث", "bluetooth headset", "سماعة جيمنج", "gaming headset", "aux"
    ],
    "mounts_and_holders": [
        "حامل", "حامل جوال", "phone stand", "tripod", "ترايبود", "selfie stick",
        "عصا سيلفي", "car mount", "bike mount", "camera lens", "عدسة كاميرا",
        "lens", "lens,"
    ],
    "storage": [
        "ذاكرة", "memory", "usb", "flash", "sd card", "micro sd", "external storage"
    ],
    "connectivity": [
        "محول", "adapter", "hdmi", "usb hub", "dongle", "sim ejector"
    ],
    "other": [
        "popsocket", "ring holder", "قلم", "stylus", "تنظيف", "cleaning kit",
        "portable speaker", "vr headset", "gaming controller", "يد تحكم",
        "fan", "cooling fan", "لوحة مفاتيح", "keyboard"
    ]
}

# ----------------------------------------
# Flatten all accessory words into one list (lowercased)
# ----------------------------------------
all_accessories = []
for category_list in accessories_search_keywords.values():
    for item in category_list:
        # ensure we handle them case-insensitively
        all_accessories.append(item.lower())


# ----------------------------------------
# Pydantic Models
# ----------------------------------------
class ProductResponse(BaseModel):
    product_id: int
    title: str
    price: float | None
    info: str | None
    link: str
    image_url: str
    store_id: int
    availability: bool
    last_old_price: float | None
    category_id: int
    group_id: int | None

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    total: int
    products: List[ProductResponse]


# ----------------------------------------
# Utility: get_search_query
# ----------------------------------------
def get_search_query(db: Session, query: str, sort_by: str):
    """
    Build the search query while carefully handling short tokens.
    """
    words = query.lower().split()  # Split query into words

    conditions = []
    # Full-query match
    conditions.append((Product.title.ilike(f"%{query}%"), 3.0))
    
    # Handle longer words normally
    for word in words:
        if len(word) > 1:  # Longer words
            conditions.append((Product.title.ilike(f"%{word}%"), 2.0))
        else:  # Single-character words
            conditions.append((
                Product.title.ilike(f"{word} %") |  # Start of word
                Product.title.ilike(f"% {word}") |  # End of word
                Product.title.ilike(f"% {word} %"),  # Middle of word
                1.5
            ))

    # Accessory condition (push accessories lower if not in query)
    from sqlalchemy import case as sql_case, or_
    accessory_condition = or_(
        *[Product.title.ilike(f"%{acc_keyword}%") for acc_keyword in all_accessories]
    )
    is_accessory_expr = sql_case(
        (accessory_condition, 1),
        else_=0
    ).label("is_accessory")

    # Relevance score
    relevance_score = sum(
        sql_case((cond, weight), else_=0.0)
        for cond, weight in conditions
    ).label("relevance")

    # Query base
    positive_conditions = [cond for cond, weight in conditions if weight > 0]
    combined_query = db.query(
        Product,
        relevance_score.label("relevance"),
        is_accessory_expr.label("is_accessory")
    ).filter(or_(*positive_conditions))

    # Sorting logic
    if sort_by == "relevance":
        combined_query = combined_query.order_by(asc("is_accessory"), desc("relevance"))
    elif sort_by == "price-low":
        combined_query = combined_query.order_by(
            asc("is_accessory"),
            case((Product.price.is_(None), 1), else_=0),
            asc(Product.price)
        )
    elif sort_by == "price-high":
        combined_query = combined_query.order_by(
            asc("is_accessory"),
            case((Product.price.is_(None), 1), else_=0),
            desc(Product.price)
        )
    elif sort_by == "newest":
        combined_query = combined_query.order_by(
            asc("is_accessory"),
            desc(Product.last_updated)
        )

    return combined_query.filter(relevance_score > 0)



# ----------------------------------------
# Utility: get_price_history
# ----------------------------------------
def get_price_history(db: Session, product_ids: List[int]) -> Dict[int, float]:
    """Get last price history for products"""
    last_price_histories = (
        db.query(ProductPriceHistory)
        .filter(ProductPriceHistory.product_id.in_(product_ids))
        .order_by(ProductPriceHistory.product_id, ProductPriceHistory.change_date.desc())
        .all()
    )
    last_old_prices = {}
    for history in last_price_histories:
        if history.product_id not in last_old_prices:
            last_old_prices[history.product_id] = history.old_price
    return last_old_prices


# ----------------------------------------
# Utility: format_product_response
# ----------------------------------------
def format_product_response(product: Product, last_old_price: float = None) -> dict:
    """Format single product response"""
    return {
        "product_id": product.product_id,
        "title": product.title,
        "price": product.price,
        "info": product.info,
        "link": product.link,
        "image_url": product.image_url,
        "store_id": product.store_id,
        "availability": product.availability,
        "category_id": product.category_id,
        "last_old_price": last_old_price,
        "group_id": product.group_id
    }


# ----------------------------------------
# Round-robin reorder by store_id
# ----------------------------------------
def reorder_by_store_round_robin(products: List[Product]) -> List[Product]:
    """
    Takes the final sorted list of products (already sorted by relevance, is_accessory, etc.),
    and rearranges them so that store IDs cycle in ascending order:
      store 1, store 2, store 3, store 1, store 2, store 3, ...
    This preserves the internal order of products within each store.
    """
    from collections import OrderedDict

    # 1) Figure out which store_ids are present, in ascending order
    store_ids = sorted({p.store_id for p in products})

    # 2) Group products by store_id in the order they appear
    store_map = OrderedDict((sid, []) for sid in store_ids)
    for prod in products:
        store_map[prod.store_id].append(prod)

    # 3) Round-robin: pick the first item from store 1, then store 2, etc.
    final_list = []
    while True:
        all_empty = True
        for sid in store_ids:
            if store_map[sid]:
                final_list.append(store_map[sid].pop(0))
                all_empty = False
        if all_empty:
            break

    return final_list


# ----------------------------------------
# Router
# ----------------------------------------
router = APIRouter(prefix="/search", tags=["search"])


# ----------------------------------------
# GET /search
# ----------------------------------------

@router.get("/quick-search", response_model=SearchResponse)
def quick_search(
    query: str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(get_db),
):
    """
    Perform a quick search with a single 'query' parameter.
    - Returns only in-stock products.
    - Fixed page size of 20.
    - Sorted by relevance.
    """
    # Build the base search query, sorted by relevance
    combined_query = get_search_query(db, query, sort_by="relevance")

    # Only in-stock products
    combined_query = combined_query.filter(Product.availability == True)

    # Count total (for completeness in response)
    total = combined_query.count()

    # Limit to 20 items (fixed page size)
    results = combined_query.limit(20).all()
    if not results:
        raise HTTPException(status_code=404, detail="No products found matching the query")

    # Extract just the Product objects from the query results
    products_only = [row[0] for row in results]

    # Reorder products in round-robin order by store_id
    reordered_products = reorder_by_store_round_robin(products_only)

    # Get price history
    product_ids = [product.product_id for product in reordered_products]
    last_old_prices = get_price_history(db, product_ids)

    # Format the products for the response
    products_response = [
        format_product_response(product, last_old_prices.get(product.product_id))
        for product in reordered_products
    ]

    return SearchResponse(total=total, products=products_response)


@router.get("/recommendations", response_model=List[ProductResponse])
def get_user_recommendations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),  # Use the updated dependency
):
    """
    Fetch and return recommended products for the logged-in user, sorted by priority.
    """
    user_id = current_user["id"]

    # Fetch recommendations, sorted by priority
    recommendations = (
        db.query(UserRecommendation)
        .filter(UserRecommendation.user_id == user_id)
        .join(Product, UserRecommendation.product_id == Product.product_id)
        .order_by(UserRecommendation.priority_score.desc())
        .limit(20)
        .all()
    )

    if not recommendations:
        raise HTTPException(status_code=404, detail="No recommendations found")

    # Extract product IDs and fetch price history
    product_ids = [rec.product.product_id for rec in recommendations]
    last_old_prices = get_price_history(db, product_ids)

    # Format response
    return [
        format_product_response(rec.product, last_old_prices.get(rec.product.product_id))
        for rec in recommendations
    ]

@router.get("/related-products", response_model=List[ProductResponse])
def get_related_products(
    group_id: Optional[int] = Query(None, description="The group ID of the product"),
    category_id: int = Query(..., description="The category ID of the product"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of related products to fetch"),
    db: Session = Depends(get_db),
):
    """
    Fetch related products based on `group_id`. If the group has too few products,
    fallback to fetching products based on `category_id`.
    """
    # Query products for the given group_id (if provided)
    group_products_query = db.query(Product).filter(Product.group_id == group_id) if group_id else None

    # Fetch products in the group if group_id is provided
    group_products = group_products_query.limit(limit).all() if group_id else []

    # If products in the group are less than the limit, fetch more from the same category
    if len(group_products) < limit:
        remaining_limit = limit - len(group_products)
        category_products_query = db.query(Product).filter(
            Product.category_id == category_id
        )
        if group_id:
            category_products_query = category_products_query.filter(Product.group_id != group_id)  # Exclude the group
        category_products = category_products_query.limit(remaining_limit).all()
    else:
        category_products = []

    # Combine the results, keeping group products first
    all_products = group_products + category_products

    # Format response
    product_ids = [product.product_id for product in all_products]
    last_old_prices = get_price_history(db, product_ids)

    return [
        format_product_response(product, last_old_prices.get(product.product_id))
        for product in all_products
    ]

@router.get("/category-products", response_model=SearchResponse)
def search_products_by_category(
    category_id: int = Query(..., description="Category ID to fetch products for"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    sort_by: Optional[str] = Query("relevance", description="Sort by: relevance, price-low, price-high, newest"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    store_filter: Optional[int] = Query(None, description="Filter by store ID"),
    in_stock_only: bool = Query(False, description="Filter by availability"),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),  # Optional dependency
):
    """
    Fetch products for a specific category with optional filters and sorting.
    """
    # Start query to fetch products by category_id
    query = db.query(Product).filter(Product.category_id == category_id)

    # Apply filters
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if store_filter is not None:
        query = query.filter(Product.store_id == store_filter)
    if in_stock_only:
        query = query.filter(Product.availability == True)

    # Apply sorting
    if sort_by == "price-low":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price-high":
        query = query.order_by(Product.price.desc())
    elif sort_by == "newest":
        query = query.order_by(Product.last_updated.desc())

    # Count total results for pagination
    total_results = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()

    # Handle case where no products are found
    if not products:
        raise HTTPException(status_code=404, detail="No products found for the given category.")

    # Get price history for the products
    product_ids = [product.product_id for product in products]
    last_old_prices = get_price_history(db, product_ids)

    # Format products for response
    response_products = [
        format_product_response(product, last_old_prices.get(product.product_id))
        for product in products
    ]

    return SearchResponse(total=total_results, products=response_products)


@router.get("/", response_model=SearchResponse)
def search_products(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Optional[str] = Query("relevance", description="Sort by: relevance, price-low, price-high, newest"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    store_filter: Optional[int] = Query(None, description="Filter by store ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    in_stock_only: bool = Query(False, description="Filter by availability"),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),  # Optional dependency
):
    """
    Search products with optional category filter
    """
    combined_query = get_search_query(db, query, sort_by)

    # Apply filters
    if store_filter is not None:
        combined_query = combined_query.filter(Product.store_id == store_filter)
    if category_id is not None:
        combined_query = combined_query.filter(Product.category_id == category_id)
    if min_price is not None:
        combined_query = combined_query.filter(Product.price >= min_price)
    if max_price is not None:
        combined_query = combined_query.filter(Product.price <= max_price)
    if in_stock_only:
        combined_query = combined_query.filter(Product.availability == True)

    # Count and paginate
    total = combined_query.count()
    offset = (page - 1) * page_size
    paginated_results = combined_query.offset(offset).limit(page_size).all()
    if not paginated_results:
        raise HTTPException(status_code=404, detail="No products found matching the query")

    products_only = [result[0] for result in paginated_results]

    # Reorder by store (if needed)
    reordered = reorder_by_store_round_robin(products_only)

    # Get price history
    product_ids = [p.product_id for p in reordered]
    last_old_prices = get_price_history(db, product_ids)

    # Log the user's search only if authenticated
    if current_user:
        search_history_entry = SearchHistory(
            user_id=current_user["id"],
            search_value=query or None,  # Use query if provided, otherwise set as NULL
        )
        db.add(search_history_entry)
        db.commit()


    # Format response
    products = [
        format_product_response(product, last_old_prices.get(product.product_id))
        for product in reordered
    ]

    return SearchResponse(total=total, products=products)



# ----------------------------------------
# GET /search/{product_id}
# ----------------------------------------
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int = Path(..., description="The ID of the product to retrieve"),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),  # Optional dependency
):
    """
    Get a single product by ID and log the view (if authenticated).
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    last_old_prices = get_price_history(db, [product_id])
    last_old_price = last_old_prices.get(product_id)

    # Log product view for signed-in user without defaulting search_value
    if current_user:
        view_history_entry = SearchHistory(
            user_id=current_user["id"],
            product_id=product_id,  # Link to the product without a search_value
        )
        db.add(view_history_entry)
        db.commit()

    return format_product_response(product, last_old_price)
