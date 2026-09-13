# SEC EDGAR インサイダー取引トラッカー — 実装仕様書

> **このドキュメントの使い方**: これはAIコーディングエージェント(Claude Code等)がこのプロジェクトを実装するための完全な仕様書です。実装を始める前に本ドキュメント全体を読み、記載された前提・制約に従ってください。曖昧な点がある場合のみユーザーに確認し、それ以外は本書に記載されたデフォルト方針で進めてください。

## 0. プロジェクトの位置づけ

米国の個人投資家向けに、SEC(米国証券取引委員会)への企業開示情報を自動で収集・記事化・公開する、**人手を介さず24時間稼働するコンテンツ事業**。姉妹プロジェクトとして議会法案トラッキングサイト(フォルダ`E`)があるが、これは独立したプロジェクトとして実装する。

- **ターゲット**: 英語圏(主に米国)の個人投資家。専門家ではなく一般投資家層
- **言語**: サイト・記事は全て英語
- **収益モデル**: 広告+証券会社アフィリエイト+将来的な有料サブスク(詳細は9章)
- **最重要な設計原則**: 完全自動化。データ取得→記事生成→品質チェック→公開→SNS告知→ニュースレター配信までの一連の流れに、日常的な人の介在を必要としない設計にすること

---

## 1. 初期スコープ(MVP)

- **対象フォームタイプ**: Form 4(インサイダー取引報告書)を最優先。これが最もSNSで拡散しやすく、記事化のパターンも定型化しやすいため
- **対象企業**: 当面はS&P 500構成銘柄(時価総額上位500社)に絞る。データ量を管理可能な範囲に収め、かつ読者にとって馴染みのある企業を優先するため
- **拡張候補(Phase 2以降)**: S-1(IPO申請書類)の要約解説、10-K/10-Qの前年比変化点まとめ
- **将来的な対象拡大**: S&P 500以外の銘柄への拡大は、Phase 1の運用が安定してから検討する

---

## 2. データソース仕様: SEC EDGAR

### 基本情報
- ベースURL: `https://data.sec.gov`
- **認証は不要**。ただし全リクエストに `User-Agent` ヘッダーが必須で、これがないと403エラーになる
  - 形式: `User-Agent: <サイト名> <連絡先メールアドレス>`
  - 例: `User-Agent: InsiderTrackerBot contact@yoursite.com`
- **レート制限**: 10リクエスト/秒。リクエスト間に最低100ms程度のウェイトを入れること
- データ形式: JSON(一部XML/HTML)

### 主要エンドポイント

| エンドポイント | 用途 |
|---|---|
| `GET /Archives/edgar/daily-index/{year}/QTR{n}/form.{yyyymmdd}.idx` | その日に提出された全書類の一覧(企業名、フォームタイプ、CIK、提出時刻、書類URLを含む)。**Form 4のスクリーニングの起点として使う** |
| `GET /submissions/CIK{10桁ゼロ埋めCIK}.json` | 特定企業の提出履歴一覧(直近の全フォームタイプ) |
| `GET /api/xbrl/companyfacts/CIK{10桁CIK}.json` | 企業の構造化財務データ(XBRL)。将来の10-K要約機能で使用 |
| 個別Form 4書類のURL(daily-indexから取得) | 提出者名、役職、取引株数、取引価格、取引日、取引種別(購入/売却)などの詳細 |

### データ取得フロー(推奨実装)

1. 毎日決まった時刻(米国東部時間の取引終了後、例: 21:00 ET)に、当日の`daily-index`ファイルを取得
2. `form.idx`からフォームタイプが`4`のレコードのみを抽出
3. 抽出したレコードのCIKを、事前に用意したS&P 500企業のCIKリスト(別途取得・保守が必要。S&P 500構成銘柄とCIKの対応表を`data/sp500_ciks.json`のようなファイルで管理する)と突合し、対象企業分のみに絞る
4. 該当する各Form 4書類のURLにアクセスし、提出者名・役職・取引株数・価格・取引種別を抽出
5. 抽出結果を構造化データ(JSON)として、後続の記事執筆エージェントに渡す

> ⚠️ SEC EDGARの技術サポートは提供されないため(公式に明記)、パース処理は自前で組み、エラーハンドリングを丁寧に行うこと。

---

## 3. コンテンツテンプレート

### テンプレート1: インサイダー取引速報(最重要)
- タイトル例: `"[Executive Name] ([Title]) Sells $[Amount] in [Company] Stock"`
- 構成: 誰が・いつ・何を・いくらで売買したか(事実) → その企業の簡単な紹介(1〜2文) → 免責事項
- 長さ: 200〜400語

### テンプレート2: 週間サマリー
- タイトル例: `"Biggest Insider Trades This Week: Top 10"`
- 構成: その週の取引額上位10件をランキング形式で紹介
- 更新頻度: 週1回(金曜日想定)

### テンプレート3(Phase 2拡張): IPOウォッチ
- タイトル例: `"[Company Name] Files for IPO: What They Do"`
- S-1提出時にトリガー

### 必須の免責事項(全記事末尾に固定文言として挿入)
```
This article is for informational purposes only and does not constitute
investment advice. Insider transactions do not necessarily indicate future
stock performance. Data is sourced from SEC EDGAR and may be subject to
delay or amendment. Always conduct your own research or consult a
licensed financial advisor before making investment decisions.
```

---

## 4. サブエージェント構成(実装版)

> 当初案では全エージェントを Claude Agent SDK 上に実装する想定だったが、実装では
> Anthropic Python SDK(Messages API、`agents/llm.py`)を直接呼び出すシンプルな
> 構成にした。①データ取得・④公開・⑤週次サマリーは**決定的コードのみ(LLM不使用)**、
> ②記事執筆・③QAの**2つだけ**が Claude を呼び出す。各呼び出しは会話履歴を持たない
> 単発リクエスト(システムプロンプト+ユーザーメッセージ)とし、エージェント間で
> コンテキストを共有しない設計は維持している。

### ①データ取得エージェント(`agents/fetch_agent.py` — 決定的コード、LLM不使用)
```
役割: S&P 500対象企業のForm 4(インサイダー取引報告書)を取得し、
構造化JSONを出力する。

実装は2戦略:
- submissions(既定): S&P 500企業ごとに /submissions/CIK*.json を辿る。
  1日あたりのリクエスト数が銘柄数(500社)で頭打ちになり、発行体が
  自明という利点がある
- daily-index: 本書2章の想定通り、当日の form.idx から Form 4 行を
  抽出し、書類を1件ずつ開いてissuer CIKをS&P 500リストと突合する
実際のHTTP取得・レート制御は agents/sec_client.py、Form 4 XMLの
パースは agents/form4_parser.py が担当する。

出力スキーマ:
{
  "filer_name": string,
  "filer_title": string,
  "company_name": string,
  "company_ticker": string,
  "transaction_date": string (YYYY-MM-DD),
  "transaction_type": "purchase" | "sale",
  "shares": number,
  "price_per_share": number,
  "total_value": number,
  "source_url": string
}

制約:
- 数値は書類から取得した値をそのまま使う。推測・計算での補完はしない
- 取得できなかった項目はnullとする
- S&P 500対象外の企業のデータは破棄する
```

### ②記事執筆エージェント(`agents/write_agent.py` — Claude呼び出し)
```
役割: データ取得エージェントの出力を基に、英語圏の一般投資家向けに
平易な英語で記事を執筆する。

制約:
- 記事中の数値・人名・企業名は入力データの値のみを使う
- 「なぜこの人物が売買したか」について、データにない推測(節税目的、
  弱気相場を見越して等)を書かない。事実の提示に徹する
- 断定的な投資判断を促す表現("buy now", "this means the stock will
  rise"等)は禁止
- 免責事項の定型文はモデルには書かせず、コード側で必ず追記する
  (常に一字一句同じ文言になるようにするため)
- 長さは200〜400語。QA側の許容幅は200〜380語、プロンプト上の目標値は
  260〜340語とし、QAで弾かれにくい範囲に収める
- 出力はMarkdown形式
```

### ③QAエージェント(`agents/qa_agent.py` — 決定的チェック+Claude呼び出し)
```
役割: 記事執筆エージェントの出力を、元データと突き合わせて検証する。

チェック項目:
1. 免責事項の有無、断定的投資助言表現の禁止ワード — 決定的コードで
   先に機械チェック(モデルを呼ぶ前に弾ける不備はここで弾く)
2. 事実確認: 記事中の金額・株数・氏名・企業名がデータと完全に一致するか — Claude
3. ハルシネーション確認: データにない事実(推測含む)が書かれていないか — Claude

出力: {"status": "approved" | "rejected", "issues": [...]}
決定的チェックとモデルレビューの両方に合格した記事のみ approved とする。
```

### ④公開エージェント(`agents/publish_agent.py` — 決定的コード、LLM不使用)
```
役割: QA承認済みの記事のみをサイトリポジトリにコミットし、
デプロイパイプラインをトリガーする。

制約:
- statusが"approved"でない記事は公開しない
- 同一取引の重複公開を防ぐため、source_url(SEC書類URL)をユニークキー
  として data/published_index.json と照合する
```

### ⑤週次サマリー(`agents/weekly_agent.py` — 決定的コード、LLM不使用/追加)
```
役割: コンテンツテンプレート2(週間サマリー、3章参照)に対応する
エージェント。当初の4章案には無かったが、実装時に専用スクリプトとして
追加した。

処理内容: 直近7日間に既に公開済みの記事(front matterの値)の中から
取引額上位10件を抽出し、ランキング形式の記事を1本
site/src/content/weekly/ に書き出す。数値は全て公開済み記事からの
転記のみで、モデル呼び出しは行わない(APIキー不要)。

実行契機: .github/workflows/weekly_summary.yml(毎週土曜)
```

### ⑥SNS運用エージェント(`agents/social_agent.py` — Phase 3、日次/週次パイプライン未組み込み)
```
役割: 公開記事から、取引額が特に大きい・著名企業であるなど
話題性のある案件を抽出し、X(旧Twitter)向けの告知文を作成する。

制約:
- 誇張表現("shocking", "huge red flag"等の煽り言葉)は避ける
- 運用初期は下書きとして保存し、人が確認してから投稿する運用とする

現状: スクリプトとしては実装済みだが、daily_pipeline / weekly_summary
どちらのワークフローにも未組み込み。手動実行のみ。X アカウントは
作成済み(有効化するかは要判断 — SETUP.md参照)。
```

### ⑦ニュースレター配信エージェント(`agents/newsletter_agent.py` — Phase 3、日次/週次パイプライン未組み込み)
```
役割: その週に公開された記事を要約し、Beehiiv向けの週次ダイジェスト
メールを作成する(下書き作成のみ自動化)。

現状: Beehiiv APIキーは取得済みだが、配信APIの利用にはMax/Enterprise
プラン(月$96〜)が必要なため、当面は下書きを人が手動でコピー&ペースト
して配信する運用に決定(自動送信への移行はプラン導入後に再検討)。
```

---

## 5. 技術スタック(実装版)

| レイヤー | 選定 |
|---|---|
| データ取得・エージェント実行基盤 | Anthropic Python SDK(Claude Messages API)を直接呼び出し。Claude Agent SDK は不使用 |
| サイト構築 | Astro(静的サイト生成、Content Layer API)。Next.jsは不採用 |
| ホスティング | GitHub Pages(独自ドメイン `decode-slang.com`、Cloudflare DNS)。Vercelは不採用 |
| メール配信 | Beehiiv(無料Launchプランのまま運用。配信APIはMax/Enterpriseプラン限定のため、送信は当面手動) |
| 自動実行 | GitHub Actions — `daily_pipeline.yml`(日次: fetch→write→qa→publish→build→deploy)、`weekly_summary.yml`(毎週土曜: 週次サマリー生成→build→deploy)、`deploy-site.yml`(`site/**`変更時に再デプロイ)、`ci.yml`(PR/push時のテスト+ビルド) |
| S&P 500構成銘柄・CIKリストの管理 | リポジトリ内の静的JSONファイル `data/sp500_ciks.json`(`data/build_sp500_ciks.py` で再生成) |

---

## 6. フォルダ構成(実装版)

```
/ (リポジトリルート)
  /agents/
    config.py            環境変数・パス設定
    sec_client.py         SEC EDGARへのHTTPクライアント(レート制御込み)
    form4_parser.py        daily-index / Form 4 XMLのパース
    articles.py            スラグ生成・front matter組み立て等の共通処理
    llm.py                Anthropic SDKのラッパー(complete_text/complete_json)
    fetch_agent.py         ①データ取得(決定的コード)
    write_agent.py         ②記事執筆(Claude呼び出し)
    qa_agent.py             ③QA(決定的チェック+Claude呼び出し)
    publish_agent.py        ④公開(決定的コード)
    weekly_agent.py         ⑤週次サマリー(決定的コード)
    social_agent.py         ⑥SNS下書き(Phase 3、未組み込み)
    newsletter_agent.py     ⑦ニュースレター下書き(Phase 3、未組み込み)
    orchestrator.py         fetch→write→qa→publishを日付単位で通しで実行
  /data/
    sp500_ciks.json         S&P 500構成銘柄とCIKの対応表
    published_index.json    公開済みfiling(source_url)の重複防止台帳
  /site/                    Astro静的サイト本体
    src/content/articles/   個別記事(Markdown、publish_agentが書き込む)
    src/content/weekly/     週次サマリー記事(Markdown、weekly_agentが書き込む)
  /output/<date>/           日次パイプラインの中間生成物(git管理外)
  /.github/workflows/
    daily_pipeline.yml
    weekly_summary.yml
    deploy-site.yml
    ci.yml
  /tests/                   test_*.py(pytest不使用、`py tests/test_x.py`で直接実行)
  README.md / CLAUDE.md / A_sec-edgar-insider-tracker_spec.md
  SETUP.md                  残タスク管理メモ
  .env.example
```

---

## 7. 環境変数(実装版 — 詳細は `.env.example` を参照)

```
# Claude / Anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-opus-5   # 高ボリューム運用時は claude-sonnet-5 へ切替でコスト削減可

# SEC EDGAR
SEC_USER_AGENT="InsiderTrackerBot you@example.com"
SEC_REQUEST_DELAY_SEC=0.15

# パイプライン動作
MIN_TOTAL_VALUE_USD=100000
OUTPUT_DIR=./output
SITE_CONTENT_DIR=./site/src/content/articles
SP500_CIKS_PATH=./data/sp500_ciks.json
PUBLISHED_INDEX_PATH=./data/published_index.json

# Phase 3+(Phase 1では未使用)
BEEHIIV_API_KEY=          # 取得済みだが配信APIはMax/Enterpriseプラン限定
BEEHIIV_PUBLICATION_ID=
X_API_KEY=                # SNS自動投稿を実装する場合
```

> `VERCEL_TOKEN` は当初案(Vercelホスティング)向けの項目だったが、実装では
> GitHub Pagesを採用したため不要・削除済み。

---

## 8. 収益化・コンプライアンス要件

- **全記事に免責事項を必須で含める**(3章の定型文を使用)
- サイトフッターに「当サイトはSEC/米国政府とは無関係の独立した情報源である」旨も明記する
- アフィリエイト: 証券会社(口座開設)のアフィリエイトリンクをサイト内に自然な形で設置(記事本文への埋め込みは最小限にし、サイドバー/フッター中心にすることで「特定の証券会社を推奨している」という印象を避ける)
- 将来の有料化(Phase 3以降)は、**既存の無料コンテンツ(速報記事)を有料化せず、新しい付加価値(複数企業のウォッチリスト機能、リアルタイム通知等)のみを有料にする**加算型モデルを厳守する

---

## 9. 実装フェーズ

| フェーズ | 内容 |
|---|---|
| Phase 1 | ①〜④エージェントをローカルで手動トリガーし、1日分のデータ取得→記事生成→QA→公開が正しく動くことを確認 |
| Phase 2 | GitHub Actionsで日次自動実行化。最低1週間、無人で正常稼働することを確認 |
| Phase 3 | ⑤SNS運用・⑥ニュースレター配信エージェントを追加。SNSは当初「下書き→人が確認→投稿」の半自動運用 |
| Phase 4 | トラフィック・購読者数を見ながら、有料サブスク機能・表示広告(Mediavine等)の導入を検討 |

---

## 10. 成功指標(初期の検証基準)

- Phase 2完了時点: パイプラインが7日間連続で無人稼働し、エラーなく記事が公開され続けること
- Phase 3完了後3ヶ月: 月間ユニーク訪問者数、ニュースレター購読者数の推移を継続計測
- 収益化判断の目安: 月間セッション数が表示広告ネットワークの参加基準(目安5万セッション/月)に近づいた時点で、Mediavine等への申請を検討
