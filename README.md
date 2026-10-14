# Climate Adaptation Simulation

本リポジトリでサポートする実行構成は、次の2つです。

- **Option 2:** React + FastAPI
- **Option 3:** React + FastAPI + Intel RealSense（任意）

旧Streamlit UI、旧React UI、Render構成、過去の解析・生成結果はサポート対象外です。

## 構成

```text
.
├── backend/       FastAPI API・シミュレーション
├── frontend/  Vite + React UI
├── camera/        RealSense入力（任意）
├── deploy/        AWS ECS/Fargate・GPU Ollama運用
├── Dockerfile
└── docker-compose.yml
```

## Option 2: React + FastAPI

前提: Python 3.12、Node.js 20以降。

### 1. FastAPI

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API確認:

```bash
curl http://127.0.0.1:8000/ping
```

### 2. React

別ターミナルで起動します。

```bash
cd frontend
npm ci
npm run dev
```

ブラウザで <http://localhost:3000> を開きます。Viteが `/api` を
`http://localhost:8000` に転送します。

AI住民機能にはOllamaを使います。Ollamaが停止中でもシミュレーション本体は動作し、
AI応答はフォールバックします。利用する場合は、バックエンド起動前に次を実行します。

```bash
ollama pull gemma4:e2b
ollama serve
```

## Option 3: RealSense（任意）

Option 2を起動したうえで、さらに2つのプロセスを起動します。

```bash
# ターミナル3: WebSocketリレー
cd frontend
npm run camera:relay

# ターミナル4: RealSense入力
cd camera
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python realsense_bridge.py
```

```text
Intel RealSense → camera/realsense_bridge.py → ws://localhost:3001 → React
```

RealSense入力はローカル表示時だけ既定で有効です。明示的に切り替える場合は
`VITE_ENABLE_CAMERA_WS=true|false` を指定します。

## Dockerでのローカル確認

```bash
export ADMIN_EXPORT_TOKEN=dev-admin-token-change-me
docker compose up --build
```

ブラウザで <http://localhost:8080> を開きます。初回はOllamaモデルの取得に時間がかかります。

## AWS

本番構成は、ALB → ECS Fargate（nginx + FastAPI）、EFS、ECR、任意のGPU EC2
（Ollama）です。手順は [deploy/README.md](deploy/README.md) を参照してください。

2026-10-13 JSTの確認時点では、AWSアカウント `082780092186` の
`ap-northeast-1` に以下がデプロイ済みです。

- ECSクラスター/サービス: `adaptation/adaptation-web`
- 稼働タスク: `1 / 1`、デプロイ状態 `COMPLETED`
- ALB: `adaptation-alb`、ターゲット `healthy`
- ECR: `adaptation-web:latest`（2026-10-06 push）

状態確認:

```bash
aws ecs describe-services \
  --region ap-northeast-1 \
  --cluster adaptation \
  --services adaptation-web
```

## テスト

```bash
cd frontend && npm run build
cd ../backend && python -m compileall .
```
