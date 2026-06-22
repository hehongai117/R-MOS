import axios from 'axios'

import { API_BASE_URL } from '@/api/client'

export interface SchoolItem {
  id: number
  name: string
  province: string | null
}

export interface TeacherItem {
  id: number
  full_name: string
  email: string
}

/** 搜索学校（公开接口，无需 token） */
export async function searchSchools(q: string, limit = 10): Promise<SchoolItem[]> {
  const res = await axios.get(`${API_BASE_URL}/api/v1/schools`, { params: { q, limit } })
  return res.data.items
}

/** 获取学校教师列表（公开接口） */
export async function listSchoolTeachers(schoolName: string): Promise<TeacherItem[]> {
  const res = await axios.get(`${API_BASE_URL}/api/v1/schools/${encodeURIComponent(schoolName)}/teachers`)
  return res.data.items
}
