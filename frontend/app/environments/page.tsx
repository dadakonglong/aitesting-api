'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function EnvironmentsRedirect() {
    const router = useRouter()

    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const project = params.get('project')
        const targetUrl = project
            ? `/settings?tab=environments&project=${project}`
            : '/settings?tab=environments'

        router.replace(targetUrl)
    }, [router])

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            color: '#6B7280'
        }}>
            <p>正在跳转到项目设置...</p>
        </div>
    )
}
