# SETUP — 残タスク・検討事項

最終更新: 2026-09-12
本番サイト: https://decode-slang.com
リポジトリ: https://github.com/nsvmm-dev/sec-edgar-insider-tracker
ロゴ・コンセプトボード: https://claude.ai/code/artifact/89bae752-8c53-4756-a44b-5c514133e4dc

> このファイルはタスク管理用のメモ。実装の詳細は `README.md` / `CLAUDE.md` / `A_sec-edgar-insider-tracker_spec.md` を参照。

---

## B. 継続監視（作業不要・時間経過で分かるもの）

- [ ] **Phase 2 の1週間無人稼働確認**：平日の daily pipeline・土曜の weekly summary が今後もエラーなく回り続けるか（仕様§10の完了基準）
- [ ] **Google Search Console のインデックス状況**：数日〜1-2週間でクロール・掲載状況を確認
- [ ] **Dependabot PR は今後も定期的に出続ける**：都度 CI green を確認してマージ、メジャー更新だけは都度相談

## C. コンテンツ拡張（要判断・未着手）

- [ ] **仕様テンプレート3（IPOウォッチ／S-1要約）**：次に作るか保留か要判断。Form 4 とは別データソースの本格追加作業になる

## D. Phase 3（SNS・ニュースレター）— 未着手

- `social_agent.py` / `newsletter_agent.py` は下書き専用で存在するが、日次/週次ワークフローに未組み込み
- 有効化には X アカウント・Beehiiv アカウントが必要（保有状況未確認）
- 組み込む場合も「下書き生成のみ自動化、投稿は手動」の運用から開始する想定

## E. マネタイズ準備（Phase 4・未着手）

- アフィリエイト：対象証券会社の選定・プログラム登録（サイドバー/フッター限定、本文には入れない方針は確定済み — 仕様§8）
- 広告：AdSense 等のアカウント取得、枠の実装（フラグで非表示にしておき、アカウント取得後に有効化する形が可能）
- 広告/トラッキング Cookie を使う場合のみ、EU向け同意バナー（CMP）が必要になる
