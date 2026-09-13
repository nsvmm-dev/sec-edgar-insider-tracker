# SETUP — 残タスク

最終更新: 2026-09-13
本番サイト: https://decode-slang.com
リポジトリ: https://github.com/nsvmm-dev/sec-edgar-insider-tracker

> このファイルはタスク管理用のメモ。実装の詳細は `README.md` / `CLAUDE.md` / `A_sec-edgar-insider-tracker_spec.md` を参照。完了した項目は都度このファイルから削除する。

---

## 継続監視（作業不要・時間経過で分かるもの）

- [ ] **Phase 2 の1週間無人稼働確認**：平日の daily pipeline・土曜の weekly summary が今後もエラーなく回り続けるか（仕様§10の完了基準）
- [ ] **Google Search Console のインデックス状況**：数日〜1-2週間でクロール・掲載状況を確認
- [ ] **Dependabot PR は今後も定期的に出続ける**：都度 CI green を確認してマージ、メジャー更新だけは都度相談

## コンテンツ拡張（要判断・未着手）

- [ ] **仕様テンプレート3（IPOウォッチ／S-1要約）**：Phase 2 の安定確認後に着手判断（本人の指示で保留中）。Form 4 とは別データソースの本格追加作業になる

## Phase 3（SNS・ニュースレター）— 未着手

- [ ] `social_agent.py` / `newsletter_agent.py` を日次/週次ワークフローに組み込むか判断・実装
- [ ] X アカウントは作成済み。Beehiiv は API キーを `.env` に登録済みだが、API 利用は Max/Enterprise プラン（月$96-109〜）が必要なため、当面は「下書きを手動でコピー&ペーストして配信」運用に決定済み

## マネタイズ（Phase 4）

- [ ] **AdSense**：サイト所有権確認タグは設置済み・審査待ち。承認後、広告枠の実装が必要
- [ ] **アフィリエイト**：Webull / Moomoo への登録手続きを本人側で実施中 — 結果（アフィリエイトリンク）待ち。取得後、サイドバー/フッター限定で掲載（本文には入れない方針は確定済み — 仕様§8）
- [ ] 広告/トラッキング Cookie を使う場合のみ、EU向け同意バナー（CMP）が必要になる
