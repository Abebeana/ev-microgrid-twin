export const rawAt = (value: string) => `raw:${value.replace(' ', 'T')}`
export const formatSiteTime = (value: string | null | undefined) =>
  value
    ? new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Europe/Berlin',
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(value))
    : 'Unavailable'
