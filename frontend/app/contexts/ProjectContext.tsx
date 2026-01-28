'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface ProjectContextType {
    currentProject: string
    setCurrentProject: (projectId: string) => void
    projects: Array<{ id: string; name: string; description: string }>
    loadProjects: () => Promise<void>
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined)

export function ProjectProvider({ children }: { children: ReactNode }) {
    const [currentProject, setCurrentProjectState] = useState<string>('default-project')
    const [projects, setProjects] = useState<Array<{ id: string; name: string; description: string }>>([])

    // 从 localStorage 加载当前项目
    useEffect(() => {
        const saved = localStorage.getItem('currentProject')
        if (saved) {
            setCurrentProjectState(saved)
        }
    }, [])

    // 加载项目列表
    const loadProjects = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects`)
            if (res.ok) {
                const data = await res.json()
                if (Array.isArray(data)) {
                    setProjects(data)
                }
            }
        } catch (error) {
            console.error('加载项目列表失败:', error)
        }
    }

    // 初始加载项目列表
    useEffect(() => {
        loadProjects()
    }, [])

    // 切换项目时保存到 localStorage
    const setCurrentProject = (projectId: string) => {
        setCurrentProjectState(projectId)
        localStorage.setItem('currentProject', projectId)
    }

    return (
        <ProjectContext.Provider value={{ currentProject, setCurrentProject, projects, loadProjects }}>
            {children}
        </ProjectContext.Provider>
    )
}

export function useProject() {
    const context = useContext(ProjectContext)
    if (context === undefined) {
        throw new Error('useProject must be used within a ProjectProvider')
    }
    return context
}
