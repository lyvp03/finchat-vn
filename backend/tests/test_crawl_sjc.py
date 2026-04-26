import requests
import json
import sys
import io
from pathlib import Path
from datetime import datetime

# Cấu hình encoding UTF-8 cho console Windows để tránh UnicodeEncodeError
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# URL API lấy giá vàng (Dùng chung cho SJC)
API_BASE = "https://www.vang.today/api/prices"

def fetch_sjc_price(days=1):
    print(f"[*] Bắt đầu gọi API lấy giá Vàng SJC trong {days} ngày qua...")
    
    # Mã SJL1L10 tương ứng với Vàng miếng SJC 1L, 10L
    params = {
        "type": "SJL1L10",
        "days": days
    }
    
    try:
        response = requests.get(API_BASE, params=params, timeout=10)
        response.raise_for_status()
        
        payload = response.json()
        if not payload.get("success"):
            print("[-] API phản hồi nhưng success = false")
            return None
            
        data = payload.get("data")
        history = payload.get("history", [])
        
        # Chỉ trích xuất thông tin cần thiết nhất
        records = []
        if history:
            for entry in history:
                date_str = entry.get("date")
                prices = entry.get("prices", {})
                
                sjc_price = prices.get("SJL1L10")
                if sjc_price:
                    records.append({
                        "thương_hiệu": "SJC",
                        "loại_vàng": "Vàng miếng (1L, 10L)",
                        "giá_mua": sjc_price.get("buy"),
                        "giá_bán": sjc_price.get("sell"),
                        "thời_gian_thu_thập": date_str
                    })
        
        print(f"[+] Đã trích xuất thành công {len(records)} bản ghi.")
        return records

    except Exception as e:
        print(f"[-] Lỗi trong quá trình gọi API: {e}")
        return None

def main():
    print("=== BƯỚC 1: TEST CRAWL DATA SJC ===")
    
    records = fetch_sjc_price(days=3)
    
    if records:
        print("\n--- KẾT QUẢ PREVIEW (Mới nhất) ---")
        for r in records[:3]: # In 3 dòng mới nhất
            print(r)
            
        # Thử lưu ra file JSON để xem bằng mắt
        output_dir = Path(__file__).resolve().parents[2] / "data"
        output_dir.mkdir(exist_ok=True)
        
        out_file = output_dir / "sjc_sample_test.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
            
        print(f"\n[+] Đã lưu toàn bộ dữ liệu mẫu ra file: {out_file}")
    else:
        print("\n[-] Không có dữ liệu để lưu.")

if __name__ == "__main__":
    main()
