"use client";
import { FormEvent, useState } from "react";

const examples = ["找出預算 300 萬到 500 萬元的資訊設備案件", "近五年有哪些道路工程決標案件？", "招決標方式如何評估？"];

export function QueryForm({ onQuery, loading }: { onQuery: (value: string) => void; loading: boolean }) {
  const [question, setQuestion] = useState("");
  function submit(event: FormEvent) { event.preventDefault(); if (question.trim()) onQuery(question.trim()); }
  return <form className="query-sheet" onSubmit={submit}>
    <label htmlFor="procurement-question">輸入採購問題</label>
    <textarea id="procurement-question" value={question} onChange={(e) => setQuestion(e.target.value)} rows={5} placeholder="輸入金額、日期、機關、案件名稱或採購程序問題" />
    <button type="submit" disabled={!question.trim() || loading}>{loading ? "整理資料中…" : "查詢公開資料"}</button>
    <div className="examples"><span>可直接試問</span>{examples.map((item) => <button type="button" key={item} onClick={() => setQuestion(item)}>{item}</button>)}</div>
  </form>;
}
