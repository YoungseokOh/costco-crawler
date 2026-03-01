import re

def parse_product_name(full_name: str) -> dict:
    """
    Parses a raw product name into its components:
    - core_name: The actual name of the product
    - origin: Origin information (e.g., 국내산, 미국)
    - weight_volume: Weight or volume (e.g., 1KG, 500ML)
    - quantity: Quantity multiplier (e.g., X 10, 10CT)
    - others: Any other modifiers (e.g., 소스포함, KG당 단가)
    """
    result = {
        'original': full_name,
        'core_name': full_name.strip(),
        'origin': None,
        'weight_volume': None,
        'quantity': None,
        'others': []
    }
    
    current_name = full_name.strip()
    
    # 1. Extract Origin
    origin_match = re.search(r'(?:원산지\s*[:_]?\s*|원산지)(.*?)(?:\s+|$)', current_name)
    if not origin_match:
         # Try to match country at the end like "호주산", "국내산" if it's clearly a suffix
         # But be careful not to match random words.
         origin_match = re.search(r'\s+([가-힣]+산)$', current_name)
         
    if origin_match:
        # Check if the matched origin is not the whole string
        if origin_match.group() != current_name:
            if '원산지' in origin_match.group():
                result['origin'] = origin_match.group(1).strip()
            else:
                 result['origin'] = origin_match.group(1).strip()
            current_name = current_name.replace(origin_match.group(0), '').strip()


    # 2. Extract specific modifiers (Others)
    others_patterns = [
        r'\(소스포함\)',
        r'등급\s*:\s*[상중하]',
        r'KG당\s*단가',
        r'도매\s*KG당단가',
        r'냉장육',
        r'냉동육'
    ]
    for pattern in others_patterns:
        match = re.search(pattern, current_name)
        if match:
            result['others'].append(match.group().strip().strip('()'))
            current_name = current_name.replace(match.group(0), '').strip()
            

    # 3. Extract Quantity
    # Matches: X 10, * 5, 10CT, 10입, 1통, 1망, 2CT/ PACK, 6인분, 7입세트, 6캔, 2세트, 24CAN, 20PK, 10(CUP), 122회, 60포
    quantity_pattern = re.search(r'(\+?\s*[xX*]\s*\d+(?:\s*CT|\s*팩|\s*입|\s*개|\s*캔|\s*세트|\s*CAN|\s*PK|\s*병|\s*박스|\s*\([^)]*\)|\s*회|\s*포)?|\s*\d+\s*(?:CT|입|통|망|팩|매|인분|입세트|캔|세트|CAN|PK|병|박스|회|포)(?:/\s*PACK)?)\s*$', current_name, re.IGNORECASE)
    if quantity_pattern:
        result['quantity'] = quantity_pattern.group(1).strip()
        current_name = current_name[:quantity_pattern.start()].strip()
        
    # Extract chained quantity (e.g. 6입 X 6팩 -> left over 6입)
    chained_quantity = re.search(r'\d+\s*(?:입|팩|매|개|회|포)\s*$', current_name)
    if chained_quantity:
        result['quantity'] = chained_quantity.group().strip() + " " + (result['quantity'] or "")
        current_name = current_name[:chained_quantity.start()].strip()


    # 4. Extract Weight/Volume
    # Matches: 1KG, 1,040G, 500G, 1.5L, 750ML and optional trailing "(...)"
    weight_pattern = re.search(
        r'\(?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:KG|G|L|ML|OZ))\s*\)?\s*(?:\(([^)]+)\))?\s*$',
        current_name,
        re.IGNORECASE,
    )
    if weight_pattern:
        base_weight = weight_pattern.group(1).strip().upper()
        trailing_info = (weight_pattern.group(2) or "").strip()

        if trailing_info:
            # Keep package breakdown as part of weight (e.g., "1KG (50G X 20)")
            if re.fullmatch(
                r'\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:KG|G|L|ML|OZ)?\s*[xX*]\s*\d+',
                trailing_info,
                re.IGNORECASE,
            ):
                result['weight_volume'] = f"{base_weight} ({trailing_info.upper()})"
            elif any(char.isdigit() for char in trailing_info) and '인분' in trailing_info:
                result['weight_volume'] = base_weight
                result['quantity'] = trailing_info
            else:
                result['weight_volume'] = base_weight
                if not any(trailing_info in other for other in result['others']):
                    result['others'].append(trailing_info)
        else:
            result['weight_volume'] = base_weight

        current_name = current_name[:weight_pattern.start()].strip()


    # 5. Final cleanup of core name
    # Remove trailing hanging brackets or hyphens
    current_name = re.sub(r'[\(\[\{\-]\s*$', '', current_name).strip()
    result['core_name'] = current_name

    return result

if __name__ == '__main__':
    # Quick static test
    samples = [
        "PURE SPECT 고당도 오렌지 3.5KG 원산지_ 미국",
        "미니 대추토마토(2KG) 원산지: 국내산",
        "고대 곡물 바게트 ANCIENT GARIN BAGUETTE 2CT_ PACK",
        "미국산 초이스 척아이롤 도매 KG당단가",
        "고메 함박 스테이크 810G (소스포함)",
        "이연복 셰프의 새우야채 춘권 1KG (50G X 20)",
        "삼립 우리밀 통단팥호빵 90G X 12"
    ]
    for s in samples:
        print(parse_product_name(s))
