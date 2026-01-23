
import json

def test_logic():
    # Mock data
    res_content = {
        "errcode": 21001,
        "errmsg": "点歌成功",
        "minute": 0
    }
    
    assertions = [
        {"field": "code", "expected": 200, "description": "code verification"},
        {"field": "message", "expected": "success", "description": "message verification"}
    ]
    
    print("Testing assertions...")
    
    for assertion in assertions:
        current_field = assertion.get("field", "")
        # --- Logic from main_sqlite.py ---
        if isinstance(res_content, dict) and "." not in current_field:
            if current_field not in res_content:
                mapping = {
                    "code": ["errcode", "RetCode", "status", "ret", "error_code"],
                    "message": ["errmsg", "msg", "info", "error", "message", "desc"],
                    "data": ["result", "content", "body", "list"]
                }
                
                if current_field in mapping:
                    for alt in mapping[current_field]:
                        if alt in res_content:
                            assertion["field"] = alt
                            print(f"   🔄 字段自动映射: {current_field} -> {alt}")
                            break
        # ---------------------------------
        
        field = assertion["field"]
        print(f"Checking field: {field}")
        
        current = res_content.get(field)
        expected = assertion["expected"]
        
        is_match = str(current) == str(expected)
        
        # --- Logic from main_sqlite.py ---
        if not is_match and field in ["message", "msg", "errmsg", "error", "info", "desc"]:
            expected_lower = str(expected).lower()
            current_str = str(current)
            
            if expected_lower in ["success", "ok"]:
                if "成功" in current_str or "ok" in current_str.lower() or "success" in current_str.lower():
                    is_match = True
                    print(f"   [Pass] {current_str} (语义匹配 Success)")
            elif str(expected) in current_str:
                is_match = True
                    
        # ---------------------------------
        
        if is_match:
            print(f"✅ Assertion Passed: {field} == {expected} (Actual: {current})")
        else:
            print(f"❌ Assertion Failed: {field} == {expected} (Actual: {current})")

test_logic()
