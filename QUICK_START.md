# Quick Start: Remove Secrets from Git History

## ⚠️ BEFORE YOU START

1. **Rotate Redis credentials FIRST!**
   - Log into Redis Cloud: https://app.redislabs.com/
   - Change your password immediately
   - Update `backend/.env` with new credentials (don't commit!)

2. **Notify your team** that Git history will be rewritten

## For Bash/Linux/Mac/Git Bash

```bash
# Make script executable
chmod +x remove_secrets.sh

# Run the script
./remove_secrets.sh
```

## For Windows PowerShell

```powershell
# Run the PowerShell script
.\remove_secrets.ps1
```

## What the Script Does

1. ✅ Creates a backup of your repository
2. ✅ Installs git-filter-repo (if needed)
3. ✅ Removes these secrets from ALL commits:
   - `redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com`
   - `QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ`
   - Port `13869`
4. ✅ Verifies secrets are removed
5. ✅ Prepares for force push

## After Running the Script

### 1. Verify Changes
```bash
# Check recent commits
git log --oneline -10

# Search for secrets (should return nothing)
git log -S "redis-13869" --all
```

### 2. Force Push to GitHub
```bash
# Push all branches
git push --force --all

# Push all tags
git push --force --tags
```

### 3. Notify Team Members

Send this message:

```
⚠️ URGENT: Git History Rewritten

We've removed leaked credentials from Git history.

ACTION REQUIRED:
1. Delete your local repository folder
2. Re-clone from GitHub:
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git

DO NOT try to pull or merge - you MUST re-clone!
```

## Troubleshooting

### "git-filter-repo: command not found"
```bash
pip install git-filter-repo
# or
pip3 install git-filter-repo
```

### "Permission denied" on Windows
```bash
# Use Git Bash instead of CMD
# Or run PowerShell as Administrator
```

### GitHub blocks force push
1. Go to GitHub → Settings → Branches
2. Temporarily disable branch protection
3. Force push
4. Re-enable branch protection

## Backup Location

Your backup is saved at: `../event-driven-platform-backup`

Don't delete it until you've verified everything works!

## Enable Secret Scanning (Prevent Future Leaks)

1. Sign up at https://www.gitguardian.com/
2. Get your API key
3. Add to GitHub: Settings → Secrets → Actions
4. Create secret: `GITGUARDIAN_API_KEY`

The CI pipeline (`.github/workflows/secret-scan.yml`) will automatically scan for secrets on every push.

---

**Need help?** See `MANUAL_HISTORY_CLEANUP.md` for detailed instructions.
