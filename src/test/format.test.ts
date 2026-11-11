import { describe, expect, it } from 'vitest'
import { clamp, formatBytes, formatDuration, titleCase } from '@/lib/format'

describe('format helpers', () => {
  it('formats media durations', () => {
    expect(formatDuration(0)).toBe('0:00')
    expect(formatDuration(65.4)).toBe('1:05')
    expect(formatDuration(600)).toBe('10:00')
  })
  it('formats file sizes and status labels', () => {
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB')
    expect(titleCase('not_ready')).toBe('Not Ready')
  })
  it('clamps trim values', () => {
    expect(clamp(12, 0, 10)).toBe(10)
    expect(clamp(-1, 0, 10)).toBe(0)
  })
})
