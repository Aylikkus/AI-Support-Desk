export type TicketStatus = 'new' | 'pending_operator' | 'processed' | 'failed'
export type OperatorRequestStatus = 'pending' | 'answered' | 'cancelled'

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
  status: TicketStatus
  error: string | null
  created_at: string
}

export interface CreatedTicket extends Ticket {
  access_token: string | null
}

export interface OperatorRequest {
  id: number
  ticket_id: number
  question: string
  answer: string | null
  status: OperatorRequestStatus
  created_at: string
  answered_at: string | null
}

export interface OperatorRequestDetail extends OperatorRequest {
  ticket: Ticket
}

async function parseError(resp: Response): Promise<Error> {
  let detail = `Ошибка запроса (${resp.status})`
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
  return new Error(detail)
}

export async function createTicket(input: TicketInput): Promise<CreatedTicket> {
  const resp = await fetch('/api/tickets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!resp.ok) throw await parseError(resp)
  return resp.json()
}

export async function listOperatorRequests(status?: OperatorRequestStatus): Promise<OperatorRequest[]> {
  const resp = await fetch(`/api/operator/requests${status ? `?status=${status}` : ''}`)
  if (!resp.ok) throw await parseError(resp)
  return resp.json()
}

export async function getOperatorRequest(id: number): Promise<OperatorRequestDetail> {
  const resp = await fetch(`/api/operator/requests/${id}`)
  if (!resp.ok) throw await parseError(resp)
  return resp.json()
}

export async function answerOperatorRequest(id: number, answer: string): Promise<OperatorRequestDetail> {
  const resp = await fetch(`/api/operator/requests/${id}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answer }),
  })
  if (!resp.ok) throw await parseError(resp)
  return resp.json()
}

export async function getTicketStatus(id: number, token: string): Promise<Ticket> {
  const resp = await fetch(`/api/tickets/${id}/status?token=${encodeURIComponent(token)}`)
  if (!resp.ok) throw await parseError(resp)
  return resp.json()
}
