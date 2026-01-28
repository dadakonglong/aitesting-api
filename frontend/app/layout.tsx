import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'AI智能接口测试平台 | 让测试更智能',
    description: '基于GPT-4的智能接口自动化测试平台，自然语言生成测试用例',
}

import Navbar from './components/Navbar'
import { ProjectProvider } from './contexts/ProjectContext'

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="zh-CN">
            <body className={inter.className} style={{
                background: 'linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 50%, #EEF2FF 100%)',
                minHeight: '100vh',
                margin: 0,
                padding: 0
            }}>
                <ProjectProvider>
                    {/* 背景装饰 */}
                    <div style={{ position: 'fixed', inset: 0, zIndex: -10, overflow: 'hidden', pointerEvents: 'none' }}>
                        <div style={{
                            position: 'absolute',
                            top: 0,
                            left: '-1rem',
                            width: '18rem',
                            height: '18rem',
                            background: '#D8B4FE',
                            borderRadius: '50%',
                            mixBlendMode: 'multiply',
                            filter: 'blur(64px)',
                            opacity: 0.2,
                            animation: 'float 3s ease-in-out infinite'
                        }}></div>
                        <div style={{
                            position: 'absolute',
                            top: 0,
                            right: '-1rem',
                            width: '18rem',
                            height: '18rem',
                            background: '#FDE047',
                            borderRadius: '50%',
                            mixBlendMode: 'multiply',
                            filter: 'blur(64px)',
                            opacity: 0.2,
                            animation: 'float 3s ease-in-out infinite 2s'
                        }}></div>
                        <div style={{
                            position: 'absolute',
                            bottom: '-2rem',
                            left: '5rem',
                            width: '18rem',
                            height: '18rem',
                            background: '#FBCFE8',
                            borderRadius: '50%',
                            mixBlendMode: 'multiply',
                            filter: 'blur(64px)',
                            opacity: 0.2,
                            animation: 'float 3s ease-in-out infinite 4s'
                        }}></div>
                    </div>

                    <Navbar />

                    <main style={{ maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem' }}>
                        {children}
                    </main>

                    {/* 页脚 */}
                    <footer style={{ marginTop: '4rem', padding: '1.5rem', textAlign: 'center', fontSize: '0.875rem', color: '#6B7280' }}>
                        <p>Powered by GPT-4 & Next.js | Made with ❤️</p>
                    </footer>

                    <style dangerouslySetInnerHTML={{
                        __html: `
                    @keyframes float {
                        0%, 100% { transform: translateY(0px); }
                        50% { transform: translateY(-10px); }
                    }
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.8; }
                    }
                `}} />
                </ProjectProvider>
            </body>
        </html>
    )
}
