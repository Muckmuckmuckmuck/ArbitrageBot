# 🚂 Railway CLI Setup Guide

## Quick Setup

To view Railway logs directly without copy-pasting:

### Step 1: Install Railway CLI

Run this command in your terminal:
```bash
bash <(curl -fsSL cli.new)
```

Or use the setup script:
```bash
bash setup_railway_cli.sh
```

### Step 2: Authenticate

```bash
railway login
```

This will open your browser to authenticate.

### Step 3: Link Your Project

In this directory (`/Users/jayreddy/Algotrading bot`):
```bash
railway link
```

When prompted, select your project: **"lively-playfulness"**

Or link directly:
```bash
railway link lively-playfulness
```

### Step 4: View Logs

**Option A: Use Python script**
```bash
python view_railway_logs.py
```

**Option B: Use Railway CLI directly**
```bash
railway logs
```

**Option C: Follow logs (live streaming)**
```bash
railway logs --follow
```

---

## After Setup

Once Railway CLI is installed and authenticated, I can run:
- `railway logs` - View current logs
- `railway logs --follow` - Stream logs in real-time
- `railway logs --tail 100` - View last 100 lines

This means I can check logs automatically without you needing to copy-paste them!

---

## Troubleshooting

**If Railway CLI is not found:**
1. Make sure it's installed: `which railway`
2. If not installed, run: `bash <(curl -fsSL cli.new)`
3. You may need to restart your terminal after installation

**If authentication fails:**
- Run `railway login` again
- Make sure you're logged into Railway in your browser

**If project linking fails:**
- Make sure you're in the project directory
- Run `railway link` and select the correct project

