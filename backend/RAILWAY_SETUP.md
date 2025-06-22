# Railway Volume Setup Instructions

## Problem
Railway uses ephemeral storage, which means all files written during runtime are lost when the container restarts. This affects our CSV data logging functionality.

## Solution
Add a Railway Volume to persist data files.

## Setup Steps

### 1. Add Volume in Railway Dashboard
1. Go to your Railway project dashboard
2. Click on your backend service
3. Go to the "Settings" tab
4. Scroll down to "Volumes" section
5. Click "Add Volume"
6. Configure:
   - **Mount Path**: `/app/data`
   - **Size**: 1GB (sufficient for CSV files)
7. Click "Add Volume"

### 2. Environment Variable (Optional)
Add this environment variable to help identify Railway environment:
- **Key**: `RAILWAY_ENVIRONMENT`
- **Value**: `true`

### 3. Redeploy
After adding the volume, redeploy your service. The data will now persist across deployments.

## File Paths
- **Local Development**: `./data/`
- **Railway Production**: `/app/data/`

## Files That Will Be Persisted
- `decision_log.csv` - User decision logs
- `block_scores.tsv` - Simulation results
- `your_name.csv` - User names
- `user_log.jsonl` - WebSocket logs

## Verification
After setup, test by:
1. Running a simulation
2. Checking if data appears in admin dashboard
3. Redeploying and verifying data persists
