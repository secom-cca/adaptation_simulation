# AWS デプロイ手順（コンテナ中心・LLM）

このドキュメントは、実装成果物を使って **ターミナル（AWS CLI）から** 本番相当環境を組むための手順です。

## 構成（S3 は使わない）

| 部品 | 役割 |
|------|------|
| **ALB** | HTTPS 入口 |
| **ECS Fargate** | 画面（nginx）+ FastAPI |
| **EFS** | `backend/data`（operation_logs など） |
| **GPU EC2** | Ollama（イベント時のみ起動） |
| ECR / ACM / CloudWatch | 周辺（イメージ・証明書・ログ） |

```text
Browser → ALB → Fargate (nginx:/ + /api→uvicorn)
                    ↓ EFS (data/)
                    ↓ OLLAMA_HOST → GPU EC2:11434 (起動中のみ)
```

## リポジトリ内の成果物

| パス | 内容 |
|------|------|
| [`Dockerfile`](../Dockerfile) | frontend build + nginx + uvicorn |
| [`docker-compose.yml`](../docker-compose.yml) | ローカル検証（web + ollama） |
| [`deploy/nginx.conf`](nginx.conf) | `/api` リバースプロキシ |
| [`deploy/entrypoint.sh`](entrypoint.sh) | コンテナ起動 |
| [`deploy/scripts/start-gpu-ollama.sh`](scripts/start-gpu-ollama.sh) | GPU 起動 + 既定 3h 自動停止予約 |
| [`deploy/scripts/stop-gpu-ollama.sh`](scripts/stop-gpu-ollama.sh) | 予約取消 + GPU 停止 |
| [`deploy/scripts/push-web-image.sh`](scripts/push-web-image.sh) | ビルド → ECR → ECS 再デプロイ |
| [`deploy/ollama/`](ollama/) | GPU EC2 上の Ollama compose |
| [`deploy/ecs/task-definition.json`](ecs/task-definition.json) | Fargate タスク定義サンプル |
| [`deploy/.env.aws.example`](.env.aws.example) | ローカル秘密設定のテンプレ |

---

## ローカル検証（Docker）

```bash
cd /path/to/adaptation_simulation
export ADMIN_EXPORT_TOKEN=dev-admin-token-change-me
docker compose up --build
# ブラウザ: http://localhost:8080
# モデル pull は ollama-pull サービスが実行（初回は時間がかかる）
```

ログ DL 試験:

```bash
curl -fsS -H "Authorization: Bearer ${ADMIN_EXPORT_TOKEN}" \
  -o operation_logs.zip \
  "http://localhost:8080/api/admin/operation-logs.zip"
```

GPU なしでも画面・シミュは動きます。AI は Ollama 未準備時フォールバックになります。

---

## A. 初回セットアップ（AWS CLI）

### A1. CLI

```bash
aws --version
aws configure   # region: ap-northeast-1 推奨
aws sts get-caller-identity
```

### A2–A3. ECR

```bash
aws ecr create-repository --repository-name adaptation-web --region ap-northeast-1
```

`repositoryUri` とアカウント ID をメモ。

### A4. ネットワーク / SG（要点）

- **ALB SG**: inbound 443（または検証用 80）from 0.0.0.0/0
- **Fargate SG**: inbound 80 from ALB SG only
- **GPU EC2 SG**: inbound **11434 from Fargate SG only**（インターネット公開しない）

デフォルト VPC + パブリックサブネットで始めるのが簡単です（本番で固めるならプライベート + NAT も可）。

### A5. EFS

```bash
aws efs create-file-system \
  --performance-mode generalPurpose \
  --encrypted \
  --region ap-northeast-1 \
  --tags Key=Name,Value=adaptation-data
```

各 AZ のアプリ用サブネットにマウントターゲットを作成し、Fargate SG から NFS（2049）を許可します。  
Access Point を切って `deploy/ecs/task-definition.json` の `fs-` / `fsap-` を置き換えてください。

コンテナ内パス `/app/backend/data` が EFS になります（`operation_logs/` 含む）。

### A6. ALB + 証明書

1. ACM で証明書（DNS 検証）  
2. ターゲットグループ（IP モード、ポート 80、ヘルスチェック `/api/ping` または `/`）  
3. ALB リスナー 443 → ターゲットグループ  
4. 公開 URL をメモ（参加者に渡す URL）

ドメインが無い場合は HTTP:80 で検証し、後から HTTPS 化してください。

### A7. ECS Fargate

```bash
aws logs create-log-group --log-group-name /ecs/adaptation-web --region ap-northeast-1
aws ecs create-cluster --cluster-name adaptation --region ap-northeast-1
```

1. `deploy/ecs/task-definition.json` の `ACCOUNT_ID` / `GPU_PRIVATE_IP` / `fs-` / `ADMIN_EXPORT_TOKEN` を編集  
2. 登録:

```bash
aws ecs register-task-definition \
  --cli-input-json file://deploy/ecs/task-definition.json \
  --region ap-northeast-1
```

3. サービス作成（サブネット・SG・ALB ターゲットグループを指定）。`desired-count` はまず `1`。

環境変数:

| 変数 | 例 |
|------|-----|
| `OLLAMA_HOST` | `http://10.0.1.23:11434`（GPU のプライベート IP） |
| `OLLAMA_MODEL` | `gemma4:e2b` |
| `LLM_MAX_CONCURRENCY` | `3` |
| `ADMIN_EXPORT_TOKEN` | 長いランダム文字列 |
| `UVICORN_WORKERS` | `2` |

### A8. GPU EC2（Ollama）— 既定は停止

1. インスタンス例: `g4dn.xlarge`、GPU 対応 AMI  
2. `deploy/ollama/` をインスタンスへ配置（例: `/opt/adaptation-ollama`）  
3. NVIDIA Container Toolkit + Docker を入れ、`docker compose up -d` → `docker compose run --rm ollama-pull`  
4. 起動時に compose が上がるよう systemd または user-data（[`ollama/user-data.sh`](ollama/user-data.sh) 参考）  
5. **作り終わったら停止:**

```bash
aws ec2 stop-instances --instance-ids i-xxxx --region ap-northeast-1
```

### A9. 自動停止用 IAM（EventBridge Scheduler）

```bash
aws iam create-role \
  --role-name adaptation-scheduler-ec2-stop \
  --assume-role-policy-document file://deploy/ecs/scheduler-trust-policy.json

aws iam put-role-policy \
  --role-name adaptation-scheduler-ec2-stop \
  --policy-name Ec2Stop \
  --policy-document file://deploy/ecs/scheduler-ec2-stop-policy.json
```

ロール ARN を控える。

### A10. 設定ファイルと初回 push

```bash
cp deploy/.env.aws.example deploy/.env.aws
# 編集: GPU_INSTANCE_ID, SCHEDULER_ROLE_ARN, AWS_ACCOUNT_ID, など

chmod +x deploy/scripts/*.sh deploy/scripts/lib.sh
./deploy/scripts/push-web-image.sh
```

### A11–A12. 動作確認

- GPU **停止**のまま URL を開き、プレイ〜 Advance（AI はフォールバックで可）  
- 短時間だけ GPU 起動（下記 B）して AI を確認し、**必ず停止**

---

## B. イベント・検証ごと（GPU）

```bash
# 開始（既定 3 時間後に自動停止）
./deploy/scripts/start-gpu-ollama.sh

# 長時間イベント
AUTO_STOP_AFTER_HOURS=6 ./deploy/scripts/start-gpu-ollama.sh

# 参加者には ALB の HTTPS URL のみ共有

# 終了（手動。予約も取り消す）
./deploy/scripts/stop-gpu-ollama.sh

# 状態確認
aws ec2 describe-instances --instance-ids "$GPU_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text
```

### タイマー再設定（延長）

起動中にもう一度 `AUTO_STOP_AFTER_HOURS=N ./deploy/scripts/start-gpu-ollama.sh` を実行すると、自動停止予約が作り直されます（インスタンスはすでに running なら start は実質 no-op）。

---

## C. 操作ログのダウンロード

```bash
export ADMIN_EXPORT_TOKEN='（タスク定義と同じ秘密）'
curl -fsS -H "Authorization: Bearer ${ADMIN_EXPORT_TOKEN}" \
  -o operation_logs.zip \
  "https://<公開URL>/api/admin/operation-logs.zip"
unzip operation_logs.zip -d ./operation_logs_downloaded
```

解凍した JSON を分析用に `backend/data/operation_logs/` 相当へ置いてスクリプトを実行してください。

---

## D. アプリ更新

```bash
./deploy/scripts/push-web-image.sh
```

環境変数や CPU を変えるときはタスク定義を編集 → `register-task-definition` → サービスが新リビジョンを使うよう更新。

| つまみ | 変更箇所 |
|--------|----------|
| 画面・シミュ負荷 | ECS CPU/メモリ、desired count |
| シミュ並列 | `UVICORN_WORKERS` |
| AI 同時数 | `LLM_MAX_CONCURRENCY` |
| AI 性能 | GPU インスタンスサイズ |

---

## E. トラブルシュート

```bash
# Fargate ログ
aws logs tail /ecs/adaptation-web --follow --region ap-northeast-1

# GPU 状態
aws ec2 describe-instances --instance-ids "$GPU_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].{State:State.Name,Type:InstanceType,PrivateIp:PrivateIpAddress}'

# 自動停止予約
aws scheduler get-schedule --name adaptation-gpu-autostop --group-name default
# 不要なら
aws scheduler delete-schedule --name adaptation-gpu-autostop --group-name default
```

混雑時は Advance に数秒〜十数秒かかることがあります（`/simulate` が年次で最大 25 回、複合シナリオではさらに並列）。

---

## イベント当日チェックリスト

1. `./deploy/scripts/start-gpu-ollama.sh`（必要なら時間指定）  
2. 自分で 1 プレイ（Advance + AI）  
3. URL を参加者へ  
4. 終了後すぐ `./deploy/scripts/stop-gpu-ollama.sh`  
5. 後日 `operation-logs.zip` を取得して分析  

**GPU を常時 ON にしないでください（料金対策）。**
