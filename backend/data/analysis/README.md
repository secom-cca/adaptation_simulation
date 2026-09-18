# analysis

操作ログ（`../operation_logs/`）などを入力に、研究・ワークショップ用の可視化・集計スクリプトを置く場所です。

## 想定構成

```text
backend/data/analysis/
├── README.md                 … 本ファイル
├── scripts/                  … 可視化・集計用 Python スクリプト
│   └── .gitkeep
└── outputs/                  … スクリプト実行結果（図・CSV・中間ファイルなど）
    ├── README.md
    └── .gitkeep
```

| パス | 役割 |
|---|---|
| `scripts/` | `operation_logs` を読む Python ファイルを複数配置する予定 |
| `outputs/` | 実行結果を下位フォルダに保存する予定（例: `outputs/20260918_summary/`） |

## 運用方針（予定）

1. 入力は原則として `backend/data/operation_logs/*.json`
2. スクリプトは `scripts/` 配下に置き、再現可能な手順を docstring または短いコメントで残す
3. 生成物は `outputs/<実行名・日付>/` など下位階層へ書き出す（リポジトリ直下や `operation_logs` 本体は汚さない）
4. 大きな生成物は Git 管理外とする想定（必要なら `.gitignore` で `outputs/**` を除外し、`.gitkeep` のみ残す）

## 現状

フォルダ骨格のみ用意しています。具体的な可視化スクリプトは今後追加予定です。
