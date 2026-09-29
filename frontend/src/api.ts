export interface TicketInput {
  customer_name: string
  customer_email: string
  message: string
}

export interface Ticket extends TicketInput {
  id: number
  category: string | null
  priority: 'low' | 'medium' | 'high' | 'urgent' | null
  summary: string | null
  reply_draft: string | null
  status: 'new' | 'processed' | 'failed'
  error: string | null
  created_at: string
}

export async function createTicket(input: TicketInput): Promise<Ticket> {
  const resp = await fetch('/api/tickets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`
    try {
      const body = await resp.json()
      if (Array.isArray(body.detail)) {
        detail = body.detail.map((d: { loc: string[]; msg: string }) => `${d.loc.at(-1)}: ${d.msg}`).join('; ')
      } else if (typeof body.detail === 'string') {
        detail = body.detail
      }
    } catch {
      /* keep default message */
    }
    throw new Error(detail)
  }
  return resp.json()
}
