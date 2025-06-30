# Deployment Guide - Vercel

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI** (optional): Install with `npm i -g vercel`

## Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Push to GitHub**: Make sure your code is pushed to GitHub
2. **Connect Repository**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your GitHub repository: `sricog/ASOCIO-FLASK`
3. **Configure Project**:
   - Framework Preset: `Other`
   - Build Command: Leave empty (Vercel will auto-detect)
   - Output Directory: Leave empty
   - Install Command: `pip install -r requirements.txt`
4. **Deploy**: Click "Deploy"

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy**:
   ```bash
   vercel
   ```

4. **Follow the prompts**:
   - Link to existing project: `No`
   - Project name: `asocio-flask` (or your preferred name)
   - Directory: `./` (current directory)

## Important Notes

### ⚠️ Limitations

1. **File System**: Vercel functions are read-only. The app won't be able to write log files.
2. **Memory**: Limited to 1024MB per function
3. **Execution Time**: Limited to 10 seconds (300 seconds for Pro plan)
4. **Dependencies**: Some heavy libraries like PuLP might cause issues

### 🔧 Modifications Made for Vercel

1. **Added `vercel.json`**: Configuration for Vercel deployment
2. **Added `wsgi.py`**: WSGI entry point for Flask
3. **Updated `requirements.txt`**: Added gunicorn for production deployment
4. **Modified `app.py`**: Disabled debug mode for production

### 🚀 Environment Variables (Optional)

You can set these in Vercel dashboard:
- `FLASK_ENV`: `production`
- `PORT`: `5000` (Vercel handles this automatically)

## Testing Your Deployment

After deployment, test these endpoints:

1. **Health Check**: `https://your-app.vercel.app/health`
2. **Main Page**: `https://your-app.vercel.app/`
3. **API Endpoint**: `https://your-app.vercel.app/resolver-instancia`

## Troubleshooting

### Common Issues

1. **Build Failures**: Check that all dependencies are in `requirements.txt`
2. **Import Errors**: Ensure all Python files are properly structured
3. **Timeout Errors**: Consider optimizing your optimization algorithm
4. **Memory Issues**: Reduce the size of your optimization problems

### Debugging

1. **Check Vercel Logs**: Go to your project dashboard → Functions → View logs
2. **Local Testing**: Test with `vercel dev` before deploying
3. **Function Logs**: Check the function logs in Vercel dashboard

## Alternative Deployment Options

If Vercel doesn't work well for your use case, consider:

1. **Heroku**: Better for long-running processes
2. **Railway**: Good for Python apps
3. **DigitalOcean App Platform**: More control over resources
4. **AWS Lambda**: For serverless with more resources

## Support

- [Vercel Documentation](https://vercel.com/docs)
- [Flask on Vercel](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [Python Runtime](https://vercel.com/docs/functions/serverless-functions/runtimes/python)