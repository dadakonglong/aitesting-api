"""
修复Headers标签页显示真实数据的脚本
"""
import re

# 读取文件
with open(r'd:\testc\aitesting-api\frontend\app\apis\page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 要替换的旧代码(硬编码的headers表格)
old_pattern = r'''                                    \{/\* Headers 标签页 \*/\}
                                    \{\(activeApiTab\[api\.id\] \|\| 'Headers'\) === 'Headers' && \(
                                        <div>
                                            <table style=\{\{ width: '100%', fontSize: '0\.8125rem', borderCollapse: 'collapse', border: '1px solid #E5E7EB', borderRadius: '0\.5rem', overflow: 'hidden' \}\}>
                                                <thead style=\{\{ background: '#F9FAFB' \}\}>
                                                    <tr>
                                                        <th style=\{\{ textAlign: 'left', padding: '0\.75rem', borderBottom: '1px solid #E5E7EB', width: '30%' \}\}>Key</th>
                                                        <th style=\{\{ textAlign: 'left', padding: '0\.75rem', borderBottom: '1px solid #E5E7EB' \}\}>Value</th>
                                                        <th style=\{\{ textAlign: 'left', padding: '0\.75rem', borderBottom: '1px solid #E5E7EB', width: '25%' \}\}>Description</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', fontWeight: '500' \}\}>Content-Type</td>
                                                        <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', color: '#3B82F6' \}\}>application/json</td>
                                                        <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', color: '#9CA3AF' \}\}>-</td>
                                                    </tr>
                                                    <tr>
                                                        <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', fontWeight: '500' \}\}>Accept</td>
                                                        <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', color: '#3B82F6' \}\}>application/json</td>
                                                        <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', color: '#9CA3AF' \}\}>-</td>
                                                    </tr>
                                                    \{api\.base_url && \(
                                                        <tr>
                                                            <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', fontWeight: '500' \}\}>Origin</td>
                                                            <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', color: '#3B82F6' \}\}>\{api\.base_url\}</td>
                                                            <td style=\{\{ padding: '0\.75rem', borderBottom: '1px solid #F3F4F6', color: '#9CA3AF' \}\}>-</td>
                                                        </tr>
                                                    \)\}
                                                </tbody>
                                            </table>
                                        </div>
                                    \)\}'''

# 新代码(显示真实headers)
new_code = '''                                    {/* Headers 标签页 */}
                                    {(activeApiTab[api.id] || 'Headers') === 'Headers' && (
                                        <div>
                                            {api.headers && Object.keys(api.headers).length > 0 ? (
                                                <table style={{ width: '100%', fontSize: '0.8125rem', borderCollapse: 'collapse', border: '1px solid #E5E7EB', borderRadius: '0.5rem', overflow: 'hidden' }}>
                                                    <thead style={{ background: '#F9FAFB' }}>
                                                        <tr>
                                                            <th style={{ textAlign: 'left', padding: '0.75rem', borderBottom: '1px solid #E5E7EB', width: '30%' }}>Key</th>
                                                            <th style={{ textAlign: 'left', padding: '0.75rem', borderBottom: '1px solid #E5E7EB' }}>Value</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {Object.entries(api.headers).map(([key, value]) => (
                                                            <tr key={key}>
                                                                <td style={{ padding: '0.75rem', borderBottom: '1px solid #F3F4F6', fontWeight: '500' }}>{key}</td>
                                                                <td style={{ padding: '0.75rem', borderBottom: '1px solid #F3F4F6', color: '#3B82F6', wordBreak: 'break-all' }}>{value}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            ) : (
                                                <p style={{ textAlign: 'center', color: '#9CA3AF', padding: '3rem' }}>暂无Headers定义</p>
                                            )}
                                        </div>
                                    )}'''

# 执行替换
content_new = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

if content_new != content:
    # 写回文件
    with open(r'd:\testc\aitesting-api\frontend\app\apis\page.tsx', 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("✅ Headers标签页已修改为显示真实数据!")
else:
    print("❌ 未找到匹配的代码,尝试手动查找...")
    # 查找Headers标签页的位置
    if '{/* Headers 标签页 */}' in content:
        print("找到Headers标签页注释")
        idx = content.find('{/* Headers 标签页 */}')
        print(f"位置: {idx}")
        print("周围代码:")
        print(content[idx:idx+500])
