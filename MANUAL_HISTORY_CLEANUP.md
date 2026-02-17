# Manual Git History Cleanup Guide

## ⚠️ CRITICAL: Leaked Credentials Found

The following Redis credentials were committed and pushed to GitHub:

- **Redis Host:** `redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com`
- **Redis Port:** `13869`
- **Redis Password:** `QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ`

## Immediate Actions Required

### 1. Rotate Redis Credentials (DO THIS FIRST!)

**Before cleaning Git history, rotate your credentials:**

1. Log into Redis Cloud: https://app.redislabs.com/
2. Navigate to your database
3. Go to "Configuration" → "Security"
4. Click "Reset Password" or "Change Password"
5. Update your local `backend/.env` file with the new password
6. **DO NOT commit the new password**

### 2. Clean Git History

Choose one of the automated scripts or follow manual steps below.

---

## Option 1: Automated Cleanup (Recommended)

### For Windows (PowerShell):

```powershell
# Run the PowerShell script
.\remove_secrets.ps1
```

### For Linux/Mac (Bash):

```bash
# Make script executable
chmod +x remove_secrets.sh

# Run the script
./remove_secrets.sh
```

---

## Option 2: Manual Cleanup with git-filter-repo

### Step 1: Install git-filter-repo

```bash
# Using pip
pip install git-filter-repo

# Or using brew (Mac)
brew install git-filter-repo
```

### Step 2: Create Backup

```bash
cd ..
git clone event-driven-platform event-driven-platform-backup
cd event-driven-platform
```

### Step 3: Create Replacement File

Create a file called `secrets.txt`:

```
redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com==>your-redis-host.cloud.redislabs.com
QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ==>your-redis-password
regex:REDIS_PORT=13869==>REDIS_PORT=your-port
```

### Step 4: Run git-filter-repo

```bash
git filter-repo --replace-text secrets.txt --force
```

### Step 5: Re-add Remote

```bash
# git-filter-repo removes remotes for safety
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
```

### Step 6: Force Push

```bash
# Push all branches
git push --force --all

# Push all tags
git push --force --tags
```

---

## Option 3: Using BFG Repo-Cleaner

### Step 1: Download BFG

Download from: https://rtyley.github.io/bfg-repo-cleaner/

```bash
# Download BFG jar file
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
```

### Step 2: Create Mirror Clone

```bash
cd ..
git clone --mirror https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO.git
```

### Step 3: Create Passwords File

Create `passwords.txt`:

```
redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com
QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ
13869
```

### Step 4: Run BFG

```bash
java -jar ../bfg-1.14.0.jar --replace-text passwords.txt
```

### Step 5: Clean and Push

```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

---

## Verification Steps

After cleaning, verify the secrets are gone:

### Check Current Files

```bash
# Should return nothing
git grep "redis-13869"
git grep "QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ"
```

### Check Git History

```bash
# Should return nothing
git log -S "redis-13869" --all
git log -S "QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ" --all

# Or use this one-liner
git grep "redis-13869" $(git rev-list --all) || echo "✅ No secrets found!"
```

### Check All Commits

```bash
# Search through all commits
git log -p --all | grep -i "redis-13869" || echo "✅ Clean!"
```

---

## Post-Cleanup Actions

### 1. Notify Team Members

Send this message to all collaborators:

```
⚠️ IMPORTANT: Git History Rewrite

We've rewritten the Git history to remove leaked credentials.

ACTION REQUIRED:
1. Delete your local repository
2. Re-clone from GitHub:
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git

DO NOT try to pull or merge - you must re-clone!
```

### 2. Update GitHub Settings

1. Go to GitHub repository settings
2. Enable "Require status checks to pass" for main branch
3. Add GitGuardian secret scanning (see CI setup)

### 3. Monitor for Unauthorized Access

1. Check Redis Cloud logs for suspicious activity
2. Review access logs for unusual patterns
3. Monitor for unexpected data changes

### 4. Enable Secret Scanning

The repository now includes:
- `.github/workflows/secret-scan.yml` - GitGuardian CI pipeline
- `.github/workflows/ci.yml` - Main CI pipeline

To activate:
1. Sign up at https://www.gitguardian.com/
2. Get your API key
3. Add to GitHub: Settings → Secrets → Actions
4. Create secret: `GITGUARDIAN_API_KEY`

---

## Troubleshooting

### Error: "remote: error: GH013: Repository rule violations"

GitHub may block the force push if branch protection is enabled.

**Solution:**
1. Go to GitHub → Settings → Branches
2. Temporarily disable branch protection
3. Force push
4. Re-enable branch protection

### Error: "fatal: refusing to merge unrelated histories"

This happens if someone tries to pull after history rewrite.

**Solution:**
They must delete and re-clone the repository.

### Error: "git-filter-repo not found"

**Solution:**
```bash
pip install git-filter-repo
# Or
pip3 install git-filter-repo
```

### BFG Error: "Repo is not a bare repository"

**Solution:**
Use `--mirror` when cloning:
```bash
git clone --mirror YOUR_REPO_URL
```

---

## Prevention Checklist

- [x] Credentials removed from current files
- [x] Git history cleanup scripts created
- [ ] Git history cleaned and force pushed
- [ ] Redis credentials rotated
- [ ] Team members notified
- [ ] GitGuardian CI enabled
- [ ] Branch protection rules updated
- [ ] Pre-commit hooks installed (optional)

---

## Additional Resources

- **git-filter-repo docs:** https://github.com/newren/git-filter-repo
- **BFG Repo-Cleaner:** https://rtyley.github.io/bfg-repo-cleaner/
- **GitGuardian:** https://www.gitguardian.com/
- **GitHub Secret Scanning:** https://docs.github.com/en/code-security/secret-scanning

---

## Support

If you encounter issues:

1. Check the backup: `../event-driven-platform-backup`
2. Review Git logs: `git log --all --oneline`
3. Verify remote: `git remote -v`
4. Check for secrets: `git log -S "redis-13869" --all`

**Remember:** The backup is your safety net. Don't delete it until you've verified everything works!

---

**Last Updated:** February 17, 2026
**Status:** Ready for execution
