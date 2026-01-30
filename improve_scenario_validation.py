#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进场景生成和验证逻辑
防止生成错误的参数映射配置
"""

def validate_param_mappings(steps: list) -> tuple[bool, list]:
    """
    验证参数映射配置
    
    Returns:
        (is_valid, errors): 是否有效和错误列表
    """
    errors = []
    
    for i, step in enumerate(steps, 1):
        step_order = step.get('step_order', i)
        param_mappings = step.get('param_mappings', [])
        
        for mapping in param_mappings:
            from_step = mapping.get('from_step')
            from_field = mapping.get('from_field')
            to_field = mapping.get('to_field')
            to_type = mapping.get('to_type', 'params')
            
            # 检查1: 自引用
            if from_step == step_order:
                errors.append({
                    'step': step_order,
                    'type': 'self_reference',
                    'message': f'步骤{step_order}不能引用自己的数据',
                    'mapping': mapping
                })
            
            # 检查2: 引用未来步骤
            elif from_step > step_order:
                errors.append({
                    'step': step_order,
                    'type': 'future_reference',
                    'message': f'步骤{step_order}不能引用后续步骤{from_step}的数据',
                    'mapping': mapping
                })
            
            # 检查3: 引用不存在的步骤
            elif from_step < 1 or from_step > len(steps):
                errors.append({
                    'step': step_order,
                    'type': 'invalid_step',
                    'message': f'步骤{step_order}引用的步骤{from_step}不存在',
                    'mapping': mapping
                })
            
            # 检查4: 缺少必要字段
            if not from_field:
                errors.append({
                    'step': step_order,
                    'type': 'missing_from_field',
                    'message': f'步骤{step_order}的映射缺少from_field',
                    'mapping': mapping
                })
            
            if not to_field:
                errors.append({
                    'step': step_order,
                    'type': 'missing_to_field',
                    'message': f'步骤{step_order}的映射缺少to_field',
                    'mapping': mapping
                })
    
    return len(errors) == 0, errors


def auto_fix_param_mappings(steps: list) -> tuple[list, list]:
    """
    自动修复参数映射配置
    
    Returns:
        (fixed_steps, fixes_applied): 修复后的步骤和应用的修复列表
    """
    fixes_applied = []
    
    for i, step in enumerate(steps, 1):
        step_order = step.get('step_order', i)
        param_mappings = step.get('param_mappings', [])
        
        # 修复1: 移除自引用
        valid_mappings = []
        for mapping in param_mappings:
            from_step = mapping.get('from_step')
            
            if from_step == step_order:
                fixes_applied.append({
                    'step': step_order,
                    'type': 'removed_self_reference',
                    'message': f'移除步骤{step_order}的自引用映射',
                    'mapping': mapping
                })
            elif from_step > step_order:
                fixes_applied.append({
                    'step': step_order,
                    'type': 'removed_future_reference',
                    'message': f'移除步骤{step_order}对未来步骤{from_step}的引用',
                    'mapping': mapping
                })
            else:
                valid_mappings.append(mapping)
        
        step['param_mappings'] = valid_mappings
    
    # 修复2: 自动添加缺失的token映射
    # 假设步骤1是登录接口
    if len(steps) > 1:
        first_step = steps[0]
        first_step_method = first_step.get('api_method', '').upper()
        first_step_path = first_step.get('api_path', '').lower()
        
        # 判断是否是登录接口
        is_login = ('login' in first_step_path or 
                   'signin' in first_step_path or
                   'auth' in first_step_path)
        
        if is_login:
            # 为后续步骤添加token映射
            for i, step in enumerate(steps[1:], 2):
                headers = step.get('headers', {})
                param_mappings = step.get('param_mappings', [])
                
                # 检查是否需要token
                needs_token = any(
                    'token' in str(v).lower() or 
                    'authorization' in k.lower()
                    for k, v in headers.items()
                )
                
                # 检查是否已有token映射
                has_token_mapping = any(
                    m.get('from_step') == 1 and
                    m.get('to_type') == 'headers' and
                    m.get('to_field', '').lower() == 'authorization'
                    for m in param_mappings
                )
                
                if needs_token and not has_token_mapping:
                    # 添加token映射
                    token_mapping = {
                        'from_step': 1,
                        'from_field': 'data.token',  # 常见的token路径
                        'to_field': 'Authorization',
                        'to_type': 'headers'
                    }
                    param_mappings.append(token_mapping)
                    step['param_mappings'] = param_mappings
                    
                    fixes_applied.append({
                        'step': i,
                        'type': 'added_token_mapping',
                        'message': f'为步骤{i}自动添加token映射',
                        'mapping': token_mapping
                    })
    
    return steps, fixes_applied


def generate_validation_report(steps: list) -> dict:
    """
    生成验证报告
    """
    is_valid, errors = validate_param_mappings(steps)
    
    report = {
        'is_valid': is_valid,
        'total_steps': len(steps),
        'total_mappings': sum(len(s.get('param_mappings', [])) for s in steps),
        'errors': errors,
        'warnings': []
    }
    
    # 添加警告
    for i, step in enumerate(steps, 1):
        param_mappings = step.get('param_mappings', [])
        
        # 警告1: 步骤1有参数映射（通常不应该有）
        if i == 1 and param_mappings:
            report['warnings'].append({
                'step': i,
                'type': 'first_step_has_mappings',
                'message': '第一个步骤通常不应该有参数映射（除非有预置数据）'
            })
        
        # 警告2: 需要认证的接口缺少token映射
        headers = step.get('headers', {})
        needs_auth = any('authorization' in k.lower() for k in headers.keys())
        has_auth_mapping = any(
            m.get('to_type') == 'headers' and 
            m.get('to_field', '').lower() == 'authorization'
            for m in param_mappings
        )
        
        if needs_auth and not has_auth_mapping and i > 1:
            report['warnings'].append({
                'step': i,
                'type': 'missing_auth_mapping',
                'message': f'步骤{i}需要认证但缺少Authorization映射'
            })
    
    return report


# 示例用法
if __name__ == "__main__":
    # 测试数据：错误的配置
    test_steps = [
        {
            'step_order': 1,
            'api_method': 'POST',
            'api_path': '/api/login',
            'headers': {},
            'param_mappings': [
                {
                    'from_step': 1,  # 错误：自引用
                    'from_field': 'data.token',
                    'to_field': 'Authorization',
                    'to_type': 'headers'
                }
            ]
        },
        {
            'step_order': 2,
            'api_method': 'POST',
            'api_path': '/api/orders',
            'headers': {
                'Authorization': 'Bearer {{token}}'
            },
            'param_mappings': []  # 错误：缺少token映射
        }
    ]
    
    print("=" * 80)
    print("🔍 验证原始配置")
    print("=" * 80)
    
    report = generate_validation_report(test_steps)
    print(f"\n验证结果: {'✅ 通过' if report['is_valid'] else '❌ 失败'}")
    print(f"总步骤数: {report['total_steps']}")
    print(f"总映射数: {report['total_mappings']}")
    
    if report['errors']:
        print(f"\n发现 {len(report['errors'])} 个错误:")
        for error in report['errors']:
            print(f"  ❌ 步骤{error['step']}: {error['message']}")
    
    if report['warnings']:
        print(f"\n发现 {len(report['warnings'])} 个警告:")
        for warning in report['warnings']:
            print(f"  ⚠️  步骤{warning['step']}: {warning['message']}")
    
    print("\n" + "=" * 80)
    print("🔧 自动修复")
    print("=" * 80)
    
    fixed_steps, fixes = auto_fix_param_mappings(test_steps)
    
    if fixes:
        print(f"\n应用了 {len(fixes)} 个修复:")
        for fix in fixes:
            print(f"  ✅ 步骤{fix['step']}: {fix['message']}")
    else:
        print("\n✅ 无需修复")
    
    print("\n" + "=" * 80)
    print("📋 修复后的配置")
    print("=" * 80)
    
    import json
    print(json.dumps(fixed_steps, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("🔍 验证修复后的配置")
    print("=" * 80)
    
    report = generate_validation_report(fixed_steps)
    print(f"\n验证结果: {'✅ 通过' if report['is_valid'] else '❌ 失败'}")
    
    if report['errors']:
        print(f"\n仍有 {len(report['errors'])} 个错误:")
        for error in report['errors']:
            print(f"  ❌ 步骤{error['step']}: {error['message']}")
    else:
        print("\n✅ 所有错误已修复")
    
    if report['warnings']:
        print(f"\n仍有 {len(report['warnings'])} 个警告:")
        for warning in report['warnings']:
            print(f"  ⚠️  步骤{warning['step']}: {warning['message']}")
