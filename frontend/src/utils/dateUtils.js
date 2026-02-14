export function formatDate(dateString) {
  if (!dateString) return ''

  try {
    const date = new Date(dateString)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}`
  } catch (error) {
    console.error('Date format error:', error)
    return dateString
  }
}

export function formatDuration(seconds) {
  if (!seconds) return '0秒'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  const parts = []
  if (hours > 0) parts.push(`${hours}小时`)
  if (minutes > 0) parts.push(`${minutes}分钟`)
  if (secs > 0) parts.push(`${secs}秒`)

  return parts.join(' ')
}

export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

export function getTimeAgo(dateString) {
  if (!dateString) return ''

  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)

  let interval = seconds / 31536000
  if (interval > 1) return Math.floor(interval) + ' 年前'

  interval = seconds / 2592000
  if (interval > 1) return Math.floor(interval) + ' 月前'

  interval = seconds / 86400
  if (interval > 1) return Math.floor(interval) + ' 天前'

  interval = seconds / 3600
  if (interval > 1) return Math.floor(interval) + ' 小时前'

  interval = seconds / 60
  if (interval > 1) return Math.floor(interval) + ' 分钟前'

  return '刚刚'
}

export function isOverdue(dueDate) {
  if (!dueDate) return false
  return new Date(dueDate) < new Date()
}

export function getDaysUntilDue(dueDate) {
  if (!dueDate) return null
  const due = new Date(dueDate)
  const now = new Date()
  const days = Math.floor((due - now) / (1000 * 60 * 60 * 24))
  return days
}
