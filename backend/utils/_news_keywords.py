"""
Keyword dictionaries for news processing.
Internal module — imported by news_classification, news_scoring, etc.
"""

DIRECT_GOLD_KEYWORDS = [
    # English
    "gold", "xauusd", "xau/usd", "bullion", "precious metal", "precious metals",
    "spot gold", "gold futures", "gold price", "gold prices", "comex gold",
    # Vietnamese
    "giá vàng", "vàng miếng", "vàng nhẫn", "vàng sjc", "sjc", "doji", "pnj",
    "bảo tín minh châu", "btmc", "vàng thế giới", "vàng trong nước", "kim loại quý",
]

MACRO_KEYWORDS = [
    # English
    "fed", "federal reserve", "fomc", "interest rate", "rate cut", "rate hike",
    "monetary policy", "hawkish", "dovish",
    "inflation", "cpi", "pce", "core pce", "nfp", "nonfarm payrolls", "jobs report",
    "unemployment", "recession", "economic slowdown", "gdp",
    "usd", "u.s. dollar", "us dollar", "dollar", "dxy",
    "treasury yield", "bond yield", "10-year yield", "real yield",
    "safe haven", "safe-haven", "geopolitical", "war", "conflict",
    "tariff", "trade war", "central bank",
    # Vietnamese
    "cục dự trữ liên bang", "lãi suất", "cắt giảm lãi suất", "tăng lãi suất",
    "chính sách tiền tệ", "lạm phát", "thất nghiệp", "suy thoái",
    "đồng usd", "đô la", "đồng bạc xanh",
    "lợi suất trái phiếu", "trái phiếu kho bạc",
    "trú ẩn an toàn", "tài sản trú ẩn", "địa chính trị",
    "chiến tranh", "xung đột", "thuế quan", "ngân hàng trung ương",
]

NOISE_KEYWORDS = [
    "gold card", "gold visa", "golden visa", "gold medal", "gold award",
    "golden globe", "goldman", "thẻ vàng", "huy chương vàng", "quả cầu vàng",
]

DOMESTIC_KEYWORDS = [
    "sjc", "doji", "pnj", "nhnn", "bảo tín", "btmc",
    "vàng miếng", "vàng nhẫn", "tỷ giá", "vàng trong nước",
]

INTL_KEYWORDS = [
    "xau", "xauusd", "fed", "cpi", "nfp", "dxy",
    "spot gold", "gold futures", "bullion", "treasury", "dollar",
]

SYMBOL_RULES = {
    "GOLD": ["gold", "giá vàng", "vàng", "bullion", "precious metal", "spot gold", "gold futures", "kim loại quý"],
    "XAUUSD": ["xauusd", "xau/usd", "spot gold"],
    "SJC": ["sjc", "vàng sjc", "vàng miếng"],
    "USD": ["usd", "u.s. dollar", "us dollar", "dollar", "đồng usd", "đô la", "đồng bạc xanh"],
    "DXY": ["dxy", "dollar index"],
    "US10Y": ["10-year yield", "treasury yield", "bond yield", "lợi suất trái phiếu", "trái phiếu kho bạc"],
    "FED": ["fed", "federal reserve", "fomc", "cục dự trữ liên bang"],
    "CPI": ["cpi", "consumer price index", "lạm phát"],
    "PCE": ["pce", "core pce"],
    "NFP": ["nfp", "nonfarm payrolls", "jobs report", "bảng lương phi nông nghiệp"],
    "VND": ["vnd", "việt nam", "trong nước"],
    "PNJ": ["pnj"],
    "DOJI": ["doji"],
    "BTMC": ["bảo tín minh châu", "btmc"],
}

TAG_RULES = {
    "gold_price": ["gold price", "gold prices", "giá vàng", "spot gold", "gold futures"],
    "domestic_gold": ["vàng trong nước", "vàng miếng", "vàng nhẫn", "sjc", "doji", "pnj", "btmc"],
    "world_gold": ["world gold", "global gold", "vàng thế giới", "spot gold", "comex gold"],
    "sjc": ["sjc", "vàng sjc", "vàng miếng"],
    "gold_ring": ["vàng nhẫn", "nhẫn trơn"],
    "fed": ["fed", "federal reserve", "fomc", "cục dự trữ liên bang"],
    "interest_rate": ["interest rate", "rate cut", "rate hike", "lãi suất", "cắt giảm lãi suất", "tăng lãi suất"],
    "usd": ["usd", "u.s. dollar", "us dollar", "dollar", "đồng usd", "đô la", "đồng bạc xanh"],
    "dxy": ["dxy", "dollar index"],
    "inflation": ["inflation", "lạm phát"],
    "cpi": ["cpi", "consumer price index"],
    "pce": ["pce", "core pce"],
    "nfp": ["nfp", "nonfarm payrolls", "jobs report"],
    "bond_yield": ["treasury yield", "bond yield", "10-year yield", "lợi suất trái phiếu"],
    "geopolitical": ["geopolitical", "war", "conflict", "địa chính trị", "chiến tranh", "xung đột"],
    "safe_haven": ["safe haven", "safe-haven", "trú ẩn an toàn", "tài sản trú ẩn"],
    "tariff": ["tariff", "trade war", "thuế quan", "chiến tranh thương mại"],
    "central_bank": ["central bank", "central banks", "ngân hàng trung ương"],
    "stock_market": ["stock market", "stocks", "equities", "chứng khoán", "cổ phiếu"],
    "oil": ["oil", "crude", "brent", "wti", "dầu"],
}

ENTITY_RULES = {
    "Fed": ["fed", "federal reserve", "fomc", "cục dự trữ liên bang"],
    "SJC": ["sjc", "vàng sjc"],
    "DOJI": ["doji"],
    "PNJ": ["pnj"],
    "Bao Tin Minh Chau": ["bảo tín minh châu", "btmc"],
    "USD": ["usd", "u.s. dollar", "us dollar", "dollar", "đồng usd", "đồng bạc xanh"],
    "DXY": ["dxy", "dollar index"],
    "CPI": ["cpi", "consumer price index"],
    "PCE": ["pce", "core pce"],
    "NFP": ["nfp", "nonfarm payrolls", "jobs report"],
    "Gold": ["gold", "giá vàng", "vàng", "bullion"],
    "Vietnam": ["việt nam", "vietnam", "trong nước"],
    "China": ["china", "trung quốc"],
    "Russia": ["russia", "nga"],
    "Ukraine": ["ukraine"],
    "Middle East": ["middle east", "trung đông"],
}

EVENT_TYPE_PRIORITY = [
    "domestic_market", "fed_policy", "inflation_data", "usd_movement",
    "bond_yield", "geopolitical_risk", "tariff_trade", "central_bank_demand",
    "economic_growth", "stock_market_risk", "gold_price_update",
]

EVENT_TYPE_RULES = {
    "domestic_market": ["vàng miếng", "vàng nhẫn", "vàng sjc", "vàng trong nước", "sjc", "doji", "pnj", "bảo tín minh châu", "btmc"],
    "fed_policy": ["fed", "federal reserve", "fomc", "interest rate", "rate cut", "rate hike", "monetary policy", "hawkish", "dovish", "cục dự trữ liên bang", "lãi suất", "cắt giảm lãi suất", "tăng lãi suất", "chính sách tiền tệ"],
    "inflation_data": ["inflation", "cpi", "pce", "core pce", "consumer price index", "lạm phát"],
    "usd_movement": ["usd", "u.s. dollar", "us dollar", "dollar", "dxy", "đồng usd", "đô la", "đồng bạc xanh"],
    "bond_yield": ["treasury yield", "bond yield", "10-year yield", "real yield", "lợi suất trái phiếu", "trái phiếu kho bạc"],
    "geopolitical_risk": ["geopolitical", "safe haven", "safe-haven", "war", "conflict", "middle east", "ukraine", "russia", "địa chính trị", "trú ẩn an toàn", "chiến tranh", "xung đột"],
    "tariff_trade": ["tariff", "trade war", "trade tension", "thuế quan", "chiến tranh thương mại"],
    "central_bank_demand": ["central bank buying", "central bank demand", "central banks", "ngân hàng trung ương mua vàng", "ngân hàng trung ương"],
    "economic_growth": ["gdp", "economic growth", "economic slowdown", "recession", "suy thoái", "tăng trưởng kinh tế"],
    "stock_market_risk": ["stock market", "stocks", "equities", "wall street", "s&p 500", "nasdaq", "chứng khoán", "cổ phiếu"],
    "gold_price_update": ["gold price", "gold prices", "spot gold", "gold futures", "bullion", "precious metals", "giá vàng", "vàng thế giới", "kim loại quý"],
}

EVENT_BASE_IMPACT = {
    "fed_policy": 0.85, "inflation_data": 0.85, "usd_movement": 0.80,
    "bond_yield": 0.80, "geopolitical_risk": 0.75, "central_bank_demand": 0.75,
    "tariff_trade": 0.65, "gold_price_update": 0.65, "domestic_market": 0.60,
    "stock_market_risk": 0.45, "economic_growth": 0.45, "other": 0.20,
}
