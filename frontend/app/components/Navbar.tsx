'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'

export default function Navbar() {
    const pathname = usePathname()

    const navItems = [
        { name: '✨ 场景生成', href: '/' },
        { name: '📋 测试管理', href: '/tests' },
        { name: '📥 数据导入', href: '/import' },
        { name: '📚 API列表', href: '/apis' },
    ]

    return (
        <nav style={{
            background: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(10px)',
            position: 'sticky',
            top: 0,
            zIndex: 50,
            borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
        }}>
            <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '0 1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', height: '4rem', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                            <div style={{ fontSize: '2rem', marginRight: '0.5rem', animation: 'pulse 2s ease-in-out infinite' }}>🤖</div>
                            <div>
                                <h1 style={{
                                    fontSize: '1.25rem',
                                    fontWeight: '700',
                                    background: 'linear-gradient(to right, #2563EB, #4F46E5, #7C3AED)',
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                    backgroundClip: 'text',
                                    margin: 0
                                }}>
                                    AI测试平台
                                </h1>
                                <p style={{ fontSize: '0.75rem', color: '#6B7280', margin: 0 }}>智能 · 高效 · 自动化</p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', marginLeft: '2.5rem', gap: '0.5rem' }}>
                            {navItems.map((item) => {
                                const isActive = pathname === item.href
                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        style={{
                                            padding: '0.5rem 1rem',
                                            borderRadius: '0.5rem',
                                            fontSize: '0.875rem',
                                            fontWeight: '500',
                                            background: isActive ? 'linear-gradient(to right, #2563EB, #4F46E5)' : 'transparent',
                                            color: isActive ? 'white' : '#374151',
                                            textDecoration: 'none',
                                            boxShadow: isActive ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        {item.name}
                                    </Link>
                                )
                            })}
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '9999px',
                            background: '#D1FAE5',
                            color: '#047857',
                            fontSize: '0.75rem',
                            fontWeight: '500'
                        }}>
                            ● 在线
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    )
}
