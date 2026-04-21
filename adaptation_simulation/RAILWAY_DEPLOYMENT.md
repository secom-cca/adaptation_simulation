# Railway Deployment Guide

## 📋 Pre-deployment Checklist

### ✅ Completed Preparation Tasks

1. **Project Structure Cleanup**
   - ✅ Removed duplicate configuration files from root directory
   - ✅ Removed duplicate backend/app directory structure
   - ✅ Unified to use files under backend directory

2. **Backend Configuration**
   - ✅ Created `railway.json` configuration file
   - ✅ Created `Procfile` backup startup file
   - ✅ Modified `run.py` to support environment variable port configuration
   - ✅ Created `.env.example` environment variable documentation
   - ✅ Complete `requirements.txt` dependency list

3. **Frontend Configuration**
   - ✅ Dynamic API address configuration (`REACT_APP_BACKEND_URL`)
   - ✅ Production environment configuration file (`.env.production`)
   - ✅ Admin page dynamic backend URL configuration

4. **Admin Features**
   - ✅ Complete Japanese interface
   - ✅ HTTP Basic authentication
   - ✅ Data download functionality
   - ✅ Dynamic backend URL configuration

## 🚀 Railway Deployment Steps

### 1. Deploy Backend to Railway

1. **Login to Railway**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login
   railway login
   ```

2. **Create New Project**
   ```bash
   cd adaptation_simulation/backend
   railway init
   ```

3. **Configure Environment Variables**
   Set in Railway Dashboard:
   ```
   ENVIRONMENT=production
   DEBUG=false
   ```

4. **Deploy Backend**
   ```bash
   railway up
   ```

5. **Get Backend URL**
   After deployment, Railway will provide a URL like:
   `https://your-app-name.railway.app`

### 2. Frontend Configuration

1. **Update Production Environment Configuration**
   Edit `frontend/.env.production`:
   ```
   REACT_APP_BACKEND_URL=https://your-backend-railway-url.railway.app
   NODE_ENV=production
   GENERATE_SOURCEMAP=false
   ```

2. **Update Admin Configuration**
   Edit `frontend/public/admin/config.js`:
   ```javascript
   // Replace 'https://your-backend-railway-url.railway.app'
   // with actual Railway backend URL
   ```

### 3. Deploy Frontend to Vercel

1. **Build Frontend**
   ```bash
   cd adaptation_simulation/frontend
   npm run build
   ```

2. **Deploy to Vercel**
   ```bash
   # Install Vercel CLI
   npm install -g vercel

   # Deploy
   vercel --prod
   ```

## 🔧 Configuration Details

### Backend Environment Variables
- `PORT`: Automatically set by Railway
- `HOST`: Default "0.0.0.0"
- `ENVIRONMENT`: "production"
- `DEBUG`: "false"

### Frontend Environment Variables
- `REACT_APP_BACKEND_URL`: Railway backend URL
- `NODE_ENV`: "production"

### Admin Access
- URL: `https://your-frontend-url.vercel.app/admin/index.html`
- Username: `admin`
- Password: `climate2025`

## 🔍 Testing Deployment

### Backend Testing
```bash
curl https://your-backend-railway-url.railway.app/ping
```

### Frontend Testing
1. Access frontend URL
2. Test simulation functionality
3. Test admin page

### Admin Functionality Testing
1. Access `/admin/index.html`
2. Login with authentication credentials
3. Test data download functionality

## 📝 Important Notes

1. **Data Persistence**: Railway's file system is ephemeral, important data should use a database
2. **CORS Configuration**: Ensure backend allows cross-origin requests from frontend domain
3. **HTTPS**: Both Railway and Vercel provide HTTPS, ensure proper configuration
4. **Environment Variables**: Configure sensitive information through environment variables, avoid hardcoding

## 🛠️ Troubleshooting

### Common Issues
1. **CORS Errors**: Check backend CORS configuration
2. **API Connection Failed**: Check frontend environment variable configuration
3. **Admin Page Inaccessible**: Check backend URL in admin configuration file

### Log Viewing
```bash
# Railway backend logs
railway logs

# Vercel frontend logs
vercel logs
```

## 📞 Support

If you encounter issues, please check:
1. Railway deployment logs
2. Browser developer tools console
3. Network request status
