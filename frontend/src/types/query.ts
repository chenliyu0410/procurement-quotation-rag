export type CaseEvidence = { id: string; title: string; text: string; source_url: string; case_id?: string; metadata: Record<string, unknown> };
export type Citation = { evidence_id: string; source_url?: string; page_number?: number };
export type PriceReference = { sample_count: number; minimum?: string; q1?: string; median?: string; q3?: string; maximum?: string; insufficient_sample: boolean; case_ids: string[] };
export type QueryResponse = { answer: string; cases: CaseEvidence[]; price_reference: PriceReference | null; citations: Citation[]; limitations: string[]; sync_metadata: { status: string } };
