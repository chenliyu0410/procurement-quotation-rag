"use client";
import { FormEvent, useState } from "react";

const examples = ["找捷運公司預算300萬到1000萬元的案件", "找與「北安抽水站抽水機引擎熱交換器檢修案」相似的案件", "依開標作業程序，開標前應通知哪些人員？"];

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
