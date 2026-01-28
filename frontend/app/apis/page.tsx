'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { FileJson, Upload } from 'lucide-react'
import APIListContent from './APIListContent'
import DataImportTab from './components/DataImportTab'

export default function APIManagementPage() {
    const searchParams = useSearchParams()
    const initialTab = searchParams?.get('tab') || 'list'
    const [activeTab, setActiveTab] = useState(initialTab)

    return (
        <div style={{ padding: '1rem 0' }}>
            {/* 页面标题 */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#111827', marginBottom: '0.5rem' }}>
                    📚 API管理
                </h1>
                <p style={{ color: '#6B7280' }}>
                    管理API接口和导入数据
                </p>
            </div>

            {/* Tab导航 */}
            <div style={{ marginBottom: '1.5rem', borderBottom: '2px solid #E5E7EB' }}>
                <div style={{ display: 'flex', gap: '2rem' }}>
                    <button
                        onClick={() => setActiveTab('list')}
                        style={{
                            padding: '0.75rem 0',
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            color: activeTab === 'list' ? '#667eea' : '#6B7280',
                            borderBottom: activeTab === 'list' ? '2px solid #667eea' : '2px solid transparent',
                            marginBottom: '-2px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <FileJson size={18} />
                        API列表
                    </button>
                    <button
                        onClick={() => setActiveTab('import')}
                        style={{
                            padding: '0.75rem 0',
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            color: activeTab === 'import' ? '#667eea' : '#6B7280',
                            borderBottom: activeTab === 'import' ? '2px solid #667eea' : '2px solid transparent',
                            marginBottom: '-2px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <Upload size={18} />
                        数据导入
                    </button>
                </div>
            </div>

            {/* Tab内容 */}
            {activeTab === 'import' ? (
                <DataImportTab />
            ) : (
                <APIListContent />
            )}
        </div>
    )
}
