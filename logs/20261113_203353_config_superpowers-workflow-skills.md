# superpowers 統合スキル2種の追加

## 何を

- `.claude/skills/superpowers-create-design/SKILL.md` を新規作成した（requirements.md / design.md / tasks.md を `docs/specs/<機能名>/` に自動作成）。
- `.claude/skills/superpowers-create-from-design-to-pr/SKILL.md` を新規作成した（ブランチ作成→設計→TDD実装→テスト・`/code-review-ocr`レビューのループ→push・PR作成・PRへのレビューコメント）。

## なぜ

- `memo/superpower_skill作成.md` の要件に基づき、superpowers のスキル群を1コマンドで連続実行できるようにするため。
- superpowers の brainstorming / writing-plans / finishing-a-development-branch は質問・承認待ちを前提とするため、「推奨案を自分で選び、仮定を文書に残して進む」無人実行ルールで上書きした。
- 自動で commit・push・PR作成を行うため、両スキルとも `disable-model-invocation: true` とし、スラッシュコマンドでの明示起動に限定した。
- レビュー修正ループは無限ループ防止のため最大3周で打ち切る。
