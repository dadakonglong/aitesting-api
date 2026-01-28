'use client'

import { useState, useEffect } from 'react'
import { useProject } from '../contexts/ProjectContext'
import { BarChart, LineChart, TrendingUp, AlertCircle, CheckCircle, Clock, Activity } from 'lucide-react'

export default function ReportsPage() {
    const { currentProject } = useProject()
    const [timeRange, setTimeRange] = useState('7d')
    const [overviewStats, setOverviewStats] = useState<any>(null)
    const [trendData, setTrendData] = useState<any[]>([])
    const [apiStats, setApiStats] = useState<any[]>([])
    const [failureAnalysis, setFailureAnalysis] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchReportData()
    }, [currentProject, timeRange])

    const fetchReportData = async () => {
        setLoading(true)
        try {
            // 获取概览统计
            const overviewRes = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/reports/overview?project_id=${currentProject}&time_range=${timeRange}`)
            const overview = await overviewRes.json()
            setOverviewStats(overview)

            // 获取趋势数据
            const trendRes = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/reports/trends?project_id=${currentProject}&metric=success_rate&days=30`)
            const trends = await trendRes.json()
            setTrendData(trends)

            // 获取API统计
            const apiRes = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/reports/api-stats?project_id=${currentProject}`)
            const apis = await apiRes.json()
            setApiStats(apis)

            // 获取失败分析
            const failureRes = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/reports/failures?project_id=${currentProject}&days=7`)
            const failures = await failureRes.json()
            setFailureAnalysis(failures)
        } catch (error) {
            console.error('获取报告数据失败:', error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
                    <div style={{ color: '#6B7280' }}>加载报告数据中...</div>
                </div>
            </div>
        )
    }

    return (
        <div style={{ padding: '2rem', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', minHeight: '100vh' }}>
            {/* 页面标题 */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: 'white', marginBottom: '0.5rem' }}>
                    📊 测试报告
                </h1>
                <p style={{ color: 'rgba(255,255,255,0.8)' }}>
                    项目: {currentProject} | 数据范围: {timeRange === '7d' ? '最近7天' : timeRange === '30d' ? '最近30天' : '最近90天'}
                </p>
            </div>

            {/* 时间范围选择 */}
            <div style={{ marginBottom: '2rem' }}>
                <select
                    value={timeRange}
                    onChange={(e) => setTimeRange(e.target.value)}
                    style={{
                        padding: '0.5rem 1rem',
                        borderRadius: '0.5rem',
                        border: '2px solid rgba(255,255,255,0.3)',
                        background: 'rgba(255,255,255,0.9)',
                        fontSize: '0.875rem',
                        fontWeight: '500',
                        cursor: 'pointer'
                    }}
                >
                    <option value="7d">最近7天</option>
                    <option value="30d">最近30天</option>
                    <option value="90d">最近90天</option>
                </select>
            </div>

            {/* 概览统计卡片 */}
            {overviewStats && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                    {/* 总执行次数 */}
                    <div style={{
                        background: 'rgba(255,255,255,0.95)',
                        borderRadius: '1rem',
                        padding: '1.5rem',
                        boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <div style={{ fontSize: '0.875rem', color: '#6B7280', fontWeight: '500' }}>总执行次数</div>
                            <Activity size={20} style={{ color: '#3B82F6' }} />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: '700', color: '#111827' }}>{overviewStats.total_executions}</div>
                        <div style={{ fontSize: '0.75rem', color: '#10B981', marginTop: '0.5rem' }}>
                            ✓ {overviewStats.success_count} 成功 | ✗ {overviewStats.failed_count} 失败
                        </div>
                    </div>

                    {/* 成功率 */}
                    <div style={{
                        background: 'rgba(255,255,255,0.95)',
                        borderRadius: '1rem',
                        padding: '1.5rem',
                        boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <div style={{ fontSize: '0.875rem', color: '#6B7280', fontWeight: '500' }}>成功率</div>
                            <CheckCircle size={20} style={{ color: '#10B981' }} />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: '700', color: '#111827' }}>
                            {(overviewStats.success_rate * 100).toFixed(1)}%
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#6B7280', marginTop: '0.5rem' }}>
                            {overviewStats.success_rate >= 0.9 ? '✨ 优秀' : overviewStats.success_rate >= 0.7 ? '👍 良好' : '⚠️ 需改进'}
                        </div>
                    </div>

                    {/* 平均响应时间 */}
                    <div style={{
                        background: 'rgba(255,255,255,0.95)',
                        borderRadius: '1rem',
                        padding: '1.5rem',
                        boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <div style={{ fontSize: '0.875rem', color: '#6B7280', fontWeight: '500' }}>平均响应时间</div>
                            <Clock size={20} style={{ color: '#F59E0B' }} />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: '700', color: '#111827' }}>
                            {overviewStats.avg_response_time}ms
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#6B7280', marginTop: '0.5rem' }}>
                            {overviewStats.avg_response_time < 200 ? '⚡ 极快' : overviewStats.avg_response_time < 500 ? '✓ 正常' : '🐌 较慢'}
                        </div>
                    </div>

                    {/* 活跃场景 */}
                    <div style={{
                        background: 'rgba(255,255,255,0.95)',
                        borderRadius: '1rem',
                        padding: '1.5rem',
                        boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <div style={{ fontSize: '0.875rem', color: '#6B7280', fontWeight: '500' }}>测试场景</div>
                            <TrendingUp size={20} style={{ color: '#8B5CF6' }} />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: '700', color: '#111827' }}>
                            {overviewStats.active_scenarios}/{overviewStats.total_scenarios}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#6B7280', marginTop: '0.5rem' }}>
                            活跃场景/总场景
                        </div>
                    </div>
                </div>
            )}

            {/* 趋势图和失败分析 */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                {/* 成功率趋势 */}
                <div style={{
                    background: 'rgba(255,255,255,0.95)',
                    borderRadius: '1rem',
                    padding: '1.5rem',
                    boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
                }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <LineChart size={20} style={{ color: '#3B82F6' }} />
                        成功率趋势
                    </h3>
                    {trendData.length > 0 ? (
                        <div style={{ height: '300px', overflowX: 'auto' }}>
                            <svg width="100%" height="280" style={{ minWidth: '600px' }}>
                                {/* 简单的折线图 */}
                                {trendData.map((point, i) => {
                                    if (i === 0) return null
                                    const prevPoint = trendData[i - 1]
                                    const x1 = (i - 1) * (600 / trendData.length)
                                    const y1 = 250 - (prevPoint.value * 200)
                                    const x2 = i * (600 / trendData.length)
                                    const y2 = 250 - (point.value * 200)
                                    return (
                                        <line
                                            key={i}
                                            x1={x1}
                                            y1={y1}
                                            x2={x2}
                                            y2={y2}
                                            stroke="#3B82F6"
                                            strokeWidth="2"
                                        />
                                    )
                                })}
                                {trendData.map((point, i) => {
                                    const x = i * (600 / trendData.length)
                                    const y = 250 - (point.value * 200)
                                    return (
                                        <circle
                                            key={i}
                                            cx={x}
                                            cy={y}
                                            r="4"
                                            fill="#3B82F6"
                                        />
                                    )
                                })}
                            </svg>
                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '3rem', color: '#9CA3AF' }}>暂无趋势数据</div>
                    )}
                </div>

                {/* 失败分析 */}
                <div style={{
                    background: 'rgba(255,255,255,0.95)',
                    borderRadius: '1rem',
                    padding: '1.5rem',
                    boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
                }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <AlertCircle size={20} style={{ color: '#EF4444' }} />
                        失败分类
                    </h3>
                    {failureAnalysis?.failure_categories?.length > 0 ? (
                        <div>
                            {failureAnalysis.failure_categories.map((cat: any, i: number) => (
                                <div key={i} style={{ marginBottom: '1rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                        <span style={{ fontSize: '0.875rem', color: '#374151' }}>{cat.category}</span>
                                        <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#EF4444' }}>{cat.count}</span>
                                    </div>
                                    <div style={{ width: '100%', height: '8px', background: '#F3F4F6', borderRadius: '4px', overflow: 'hidden' }}>
                                        <div style={{
                                            width: `${(cat.count / failureAnalysis.failure_categories[0].count) * 100}%`,
                                            height: '100%',
                                            background: 'linear-gradient(to right, #EF4444, #DC2626)',
                                            borderRadius: '4px'
                                        }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '2rem', color: '#9CA3AF' }}>暂无失败数据</div>
                    )}
                </div>
            </div>

            {/* API统计表格 */}
            <div style={{
                background: 'rgba(255,255,255,0.95)',
                borderRadius: '1rem',
                padding: '1.5rem',
                boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
            }}>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <BarChart size={20} style={{ color: '#8B5CF6' }} />
                    接口统计 (Top 20)
                </h3>
                {apiStats.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ background: '#F9FAFB', borderBottom: '2px solid #E5E7EB' }}>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>接口</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>执行次数</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>成功</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>失败</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>成功率</th>
                                </tr>
                            </thead>
                            <tbody>
                                {apiStats.map((api, i) => (
                                    <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                        <td style={{ padding: '0.75rem', fontSize: '0.875rem', fontWeight: '500' }}>{api.api_name}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.875rem' }}>{api.total_executions}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.875rem', color: '#10B981' }}>{api.success_count}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.875rem', color: '#EF4444' }}>{api.failed_count}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.875rem', fontWeight: '600' }}>
                                            <span style={{
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '0.375rem',
                                                background: api.success_rate >= 0.9 ? '#D1FAE5' : api.success_rate >= 0.7 ? '#FEF3C7' : '#FEE2E2',
                                                color: api.success_rate >= 0.9 ? '#065F46' : api.success_rate >= 0.7 ? '#92400E' : '#991B1B'
                                            }}>
                                                {(api.success_rate * 100).toFixed(1)}%
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div style={{ textAlign: 'center', padding: '3rem', color: '#9CA3AF' }}>暂无接口统计数据</div>
                )}
            </div>
        </div>
    )
}
