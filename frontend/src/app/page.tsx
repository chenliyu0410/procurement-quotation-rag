const exampleQuestion = "找出預算 300 萬到 500 萬元的資訊設備案件";

export default function Home() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">TenderLens</p>
        <h1>採購與報價知識助理</h1>
        <p className="lead">
          查詢臺北市公開採購資料、比較歷史決標金額，並取得可追溯的文件依據。
        </p>

        <form className="query-card">
          <label htmlFor="procurement-question">輸入採購問題</label>
          <textarea
            id="procurement-question"
            name="question"
            placeholder="例如：有哪些資訊設備相關的歷史標案？"
            rows={4}
          />
          <button type="submit">開始查詢</button>
        </form>

        <div className="example">
          <span>範例問題</span>
          <p>{exampleQuestion}</p>
        </div>
      </section>
    </main>
  );
}
