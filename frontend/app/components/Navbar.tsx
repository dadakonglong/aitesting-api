'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { useProject } from '../contexts/ProjectContext'
import { FolderOpen } from 'lucide-react'

export default function Navbar() {
    const pathname = usePathname()
    const { currentProject, setCurrentProject, projects } = useProject()

    const navItems = [
        { name: '🧪 测试中心', href: '/testing' },
        { name: '📚 API管理', href: '/apis' },
        { name: '📊 测试报告', href: '/reports' },
        { name: '⚙️ 项目设置', href: '/settings' },
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
                                const isActive = pathname === item.href ||
                                    (item.href === '/testing' && (pathname === '/' || pathname === '/tests' || pathname === '/scheduler')) ||
                                    (item.href === '/apis' && pathname === '/import') ||
                                    (item.href === '/settings' && (pathname === '/projects' || pathname === '/environments'))
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

                    {/* 全局项目选择器 */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <FolderOpen size={18} style={{ color: '#6B7280' }} />
                        <select
                            value={currentProject}
                            onChange={(e) => setCurrentProject(e.target.value)}
                            style={{
                                padding: '0.5rem 2.5rem 0.5rem 1rem',
                                border: '2px solid #E5E7EB',
                                borderRadius: '0.5rem',
                                fontSize: '0.875rem',
                                fontWeight: '600',
                                color: '#1F2937',
                                background: 'white',
                                cursor: 'pointer',
                                outline: 'none',
                                appearance: 'none',
                                backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'12\' height=\'12\' viewBox=\'0 0 12 12\'%3E%3Cpath fill=\'%236B7280\' d=\'M6 9L1 4h10z\'/%3E%3C/svg%3E")',
                                backgroundRepeat: 'no-repeat',
                                backgroundPosition: 'right 0.75rem center',
                                minWidth: '180px'
                            }}
                        >
                            {projects.length === 0 ? (
                                <option value="default-project">默认项目</option>
                            ) : (
                                projects.map((project) => (
                                    <option key={project.id} value={project.id}>
                                        {project.name}
                                    </option>
                                ))
                            )}
                        </select>
                    </div>
                </div>
            </div>
        </nav>
    )
}
