import json
import pytest
from crawler.utils.name_parser import parse_product_name

def load_products():
    try:
        with open('data/current/products.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return data.get('products', [])
    except Exception as e:
        print(f"Error loading data: {e}")
        return []

PRODUCTS = load_products()
NAMES = [p.get('product_name', '') for p in PRODUCTS if p.get('product_name')]

def test_data_loaded():
    assert len(NAMES) > 0, "No products loaded from data/current/products.json"

@pytest.mark.parametrize("name", NAMES)
def test_parse_product_name(name):
    # This test simply ensures the parser doesn't crash on any real data
    # and that the core_name is extracted and is not empty.
    result = parse_product_name(name)
    assert 'core_name' in result
    assert result['core_name'], f"Core name should not be empty for {name}"
    # Verify that original is maintained
    assert result['original'] == name

def test_specific_known_patterns():
    # Test specific edge cases found in the data
    
    # 1. Complex weight with parenthesis
    res1 = parse_product_name("이연복 셰프의 새우야채 춘권 1KG (50G X 20)")
    assert res1['core_name'] == "이연복 셰프의 새우야채 춘권"
    assert res1['weight_volume'] == "1KG (50G X 20)"
    
    # 2. Origin with various separators
    res2 = parse_product_name("PURE SPECT 고당도 오렌지 3.5KG 원산지_ 미국")
    assert res2['core_name'] == "PURE SPECT 고당도 오렌지"
    assert res2['origin'] == "미국"
    assert res2['weight_volume'] == "3.5KG"
    
    # 3. Simple quantity and weight
    res3 = parse_product_name("삼립 우리밀 통단팥호빵 90G X 12")
    assert res3['core_name'] == "삼립 우리밀 통단팥호빵"
    assert res3['weight_volume'] == "90G"
    assert res3['quantity'] == "X 12"

    # 4. Modifiers
    res4 = parse_product_name("고메 함박 스테이크 810G (소스포함)")
    assert res4['core_name'] == "고메 함박 스테이크"
    assert "소스포함" in res4['others']
    assert res4['weight_volume'] == "810G"
    
    # 5. Korean origin at the end without "원산지:"
    res5 = parse_product_name("미국산 초이스 척아이롤 도매 KG당단가")
    assert res5['core_name'] == "미국산 초이스 척아이롤 도매"
    assert "KG당단가" in res5['others']

def get_parsing_stats():
    """Helper to print out statistics of how well the parser is doing overall"""
    parsed = [parse_product_name(n) for n in NAMES]
    
    with_origin = sum(1 for p in parsed if p['origin'])
    with_weight = sum(1 for p in parsed if p['weight_volume'])
    with_qty = sum(1 for p in parsed if p['quantity'])
    with_others = sum(1 for p in parsed if p['others'])
    
    print("\n--- Parsing Statistics ---")
    print(f"Total Products: {len(NAMES)}")
    print(f"Products with Origin recognized: {with_origin}")
    print(f"Products with Weight/Volume recognized: {with_weight}")
    print(f"Products with Quantity recognized: {with_qty}")
    print(f"Products with Other modifiers recognized: {with_others}")
    
    print("\n--- Examples of Fully Parsed Items ---")
    count = 0
    for p in parsed:
        if p['origin'] and p['weight_volume'] and p['quantity']:
            print(f"Original: {p['original']}")
            print(f" -> core: {p['core_name']} | wt/vol: {p['weight_volume']} | qty: {p['quantity']} | origin: {p['origin']}")
            count += 1
            if count > 5: break
            
if __name__ == '__main__':
    get_parsing_stats()
