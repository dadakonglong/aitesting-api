#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比成功和失败的执行记录
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def compare_executions():
    print("=" * 80)
    print("🔍 对比成功和失败的执行")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 查找ID37的最新成功执行
    print("\n📊 查找ID37的最新执行:")
    
    c.execute("SELECT test_case_id FROM scenarios WHERE id = 37")
    scenario37 = c.fetchone()
    
    if scenario37:
        test_case_id_37 = scenario37['test_case_id']
        
        c.execute("""
            SELECT * FROM executions 
            WHERE test_case_id = ? 
            ORDER BY id DESC 
            LIMIT 1
        """, (test_case_id_37,))
        
        exec37 = c.fetchone()
        
        if exec37:
            print(f"   ✅ 找到ID37最新执行: {exec37['id']} ({exec37['status']})")
            results37 = json.loads(exec37['results'])
        else:
            print("   ❌ 找不到ID37的执行记录")
            conn.close()
            return
    else:
        print("   ❌ 找不到场景37")
        conn.close()
        return
    
    # 2. 查找ID58的最新失败执行
    print("\n📊 查找ID58的最新执行:")
    
    c.execute("SELECT test_case_id FROM scenarios WHERE id = 58")
    scenario58 = c.fetchone()
    
    if scenario58:
        test_case_id_58 = scenario58['test_case_id']
        
        c.execute("""
            SELECT * FROM executions 
            WHERE test_case_id = ? 
            ORDER BY id DESC 
            LIMIT 1
        """, (test_case_id_58,))
        
        exec58 = c.fetchone()
        
        if exec58:
            print(f"   ✅ 找到ID58最新执行: {exec58['id']} ({exec58['status']})")
            results58 = json.loads(exec58['results'])
        else:
            print("   ❌ 找不到ID58的执行记录")
            conn.close()
            return
    else:
        print("   ❌ 找不到场景58")
        conn.close()
        return
    
    # 3. 详细对比步骤2
    print("\n" + "=" * 80)
    print("🔍 详细对比步骤2 (关键步骤):")
    print("=" * 80)
    
    if len(results37) >= 2 and len(results58) >= 2:
        step2_37 = results37[1]
        step2_58 = results58[1]
        
        print(f"\n📋 基本信息:")
        print(f"   ID37: {step2_37.get('method')} {step2_37.get('status_code')} - {step2_37.get('success')}")
        print(f"   ID58: {step2_58.get('method')} {step2_58.get('status_code')} - {step2_58.get('success')}")
        
        # 对比URL
        print(f"\n🌐 URL对比:")
        print(f"   ID37: {step2_37.get('url')}")
        print(f"   ID58: {step2_58.get('url')}")
        
        # 对比请求头
        print(f"\n📤 请求头对比:")
        headers37 = step2_37.get('request_headers', {})
        headers58 = step2_58.get('request_headers', {})
        
        # 关键请求头
        key_headers = ['Authorization', 'X-Employee-Id', 'X-Venue-Id', 'X-Mac', 'Content-Type']
        
        for header in key_headers:
            val37 = headers37.get(header, '(缺失)')
            val58 = headers58.get(header, '(缺失)')
            
            if val37 == val58:
                print(f"   ✅ {header}: 相同")
            else:
                print(f"   ❌ {header}:")
                print(f"      ID37: {val37}")
                print(f"      ID58: {val58}")
        
        # 对比请求参数
        print(f"\n📝 请求参数对比:")
        params37 = step2_37.get('request_data', {})
        params58 = step2_58.get('request_data', {})
        
        # 关键参数
        key_params = ['venueId', 'employeeId', 'roomId', 'sessionId', 'startTime', 'endTime', 'payAmount']
        
        for param in key_params:
            val37 = params37.get(param, '(缺失)')
            val58 = params58.get(param, '(缺失)')
            
            if val37 == val58:
                print(f"   ✅ {param}: 相同")
            else:
                print(f"   ❌ {param}:")
                print(f"      ID37: {val37}")
                print(f"      ID58: {val58}")
        
        # 对比响应
        print(f"\n📥 响应对比:")
        resp37 = step2_37.get('response', {})
        resp58 = step2_58.get('response', {})
        
        if isinstance(resp37, dict) and isinstance(resp58, dict):
            code37 = resp37.get('code')
            code58 = resp58.get('code')
            msg37 = resp37.get('message')
            msg58 = resp58.get('message')
            
            print(f"   ID37: code={code37}, message={msg37}")
            print(f"   ID58: code={code58}, message={msg58}")
            
            if code37 == 0 and code58 == 4200:
                print(f"\n   💡 分析:")
                print(f"      ID37成功 (code=0)")
                print(f"      ID58失败 (code=4200: 门店授权码无效)")
                print(f"      可能原因:")
                print(f"      1. 请求参数不同")
                print(f"      2. 时间戳过期")
                print(f"      3. 房间状态不同")
                print(f"      4. 员工权限不同")
        
        # 对比提取记录
        print(f"\n🔄 提取记录对比:")
        ext37 = step2_37.get('extractions', [])
        ext58 = step2_58.get('extractions', [])
        
        print(f"   ID37提取记录: {len(ext37)}个")
        for ext in ext37:
            status = "✅" if ext.get('success') else "❌"
            print(f"      {status} {ext.get('from_field')} -> {ext.get('to_type')}.{ext.get('to_field')}")
        
        print(f"   ID58提取记录: {len(ext58)}个")
        for ext in ext58:
            status = "✅" if ext.get('success') else "❌"
            print(f"      {status} {ext.get('from_field')} -> {ext.get('to_type')}.{ext.get('to_field')}")
    
    conn.close()
    
    print(f"\n" + "=" * 80)
    print(f"💡 结论:")
    print("=" * 80)
    print("""
如果Token提取都正确，但ID58仍然失败，可能的原因：

1. 请求参数差异 - 检查关键业务参数
2. 时间相关参数 - startTime, endTime可能过期
3. 房间状态 - roomId对应的房间可能已被占用
4. 员工权限 - employeeId对应的员工权限不同
5. 门店配置 - venueId对应的门店配置不同

建议：
1. 对比成功和失败的请求参数差异
2. 检查时间戳是否合理
3. 确认房间和员工状态
    """)

if __name__ == "__main__":
    compare_executions()