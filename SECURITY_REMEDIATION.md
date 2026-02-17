# Security Remediation Guide

## Leaked Redis Credentials - Action Required

### Critical Findings

The following Redis credentials were exposed in Git history:

1. **Redis Host:** `redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com`
2. **Redis Port:** `13869`
3. **Redis Password:** `QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ`

### Files Affected

- `DOCUMENTATION.md` (cleaned)
- `DEPLOYMENT.md` (cleaned)
- `FREE-TIER-DEPLOYMENT.md` (cleaned)
- `backend/.env.example` (cleaned)

All files have been updated with placeholder values, but the credentials still exist in Git history.

### Immediate Actions

1. **Rotate Redis Credentials**
   - Log into Redis Cloud console
   - Change the password for your Redis instance
   - Update `backend/.env` with new credentials
   - **DO NOT commit the new credentials**

2. **Remove Credentials from Git History**

The leaked credentials exist in the Git history and need to be removed. Choose one method:

#### Method 1: Using BFG Repo-Cleaner (Recommended)

```bash
# Install BFG (requires Java)
# Download from: https://rtyley.github.io/bfg-repo-cleaner/

# Clone a fresh copy
git clone --mirror https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Remove the sensitive data
java -jar bfg.jar --replace-text passwords.txt YOUR_REPO.git

# Create passwords.txt with:
redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com==>REMOVED
QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ==>REMOVED
13869==>REMOVED

# Clean up
cd YOUR_REPO.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push --force
```

#### Method 2: Using git filter-repo

```bash
# Install git-filter-repo
pip install git-filter-repo

# Backup your repo first
git clone YOUR_REPO.git YOUR_REPO_backup

# Remove sensitive file versions
git filter-repo --path DOCUMENTATION.md --invert-paths --force

# Or replace text in history
git filter-repo --replace-text <(echo "redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com==>REDACTED")

# Force push
git push --force --all
```

#### Method 3: Manual History Rewrite (Advanced)

```bash
# Interactive rebase to edit commits
git rebase -i --root

# For each commit with leaked data, mark as 'edit'
# Then amend the commit:
git commit --amend
git rebase --continue

# Force push
git push --force
```

### Post-Remediation Steps

1. **Verify Removal**
   ```bash
   # Search for leaked credentials
   git log -S "redis-13869" --all
   git grep "redis-13869" $(git rev-list --all)
   ```

2. **Notify Team**
   - Inform all collaborators about the force push
   - Ask them to re-clone the repository
   - Ensure no one has the old credentials cached

3. **Update Documentation**
   - Confirm DOCUMENTATION.md uses placeholder values
   - Review all files for sensitive data

4. **Enable GitGuardian**
   - Sign up at https://www.gitguardian.com/
   - Get API key from dashboard
   - Add as GitHub secret: `GITGUARDIAN_API_KEY`
   - The workflow will automatically scan for secrets

### Prevention

1. **Use .env files** (already in .gitignore)
2. **Enable GitGuardian CI** (configured in `.github/workflows/secret-scan.yml`)
3. **Pre-commit hooks** (optional, see below)
4. **Regular security audits**

### Optional: Pre-commit Hook

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/gitguardian/ggshield
    rev: v1.25.0
    hooks:
      - id: ggshield
        language_version: python3
        stages: [commit]
EOF

# Install hooks
pre-commit install
```

## GitHub Repository Settings

### Required Secrets

Add these to GitHub Settings → Secrets and variables → Actions:

- `GITGUARDIAN_API_KEY`: Your GitGuardian API key

### Branch Protection Rules

Enable for `main` branch:
- ✅ Require pull request reviews
- ✅ Require status checks to pass (CI Pipeline, GitGuardian Scan)
- ✅ Require branches to be up to date
- ✅ Do not allow bypassing the above settings

## Monitoring

- GitGuardian will scan on every PR and push
- Weekly scheduled scans on Mondays
- Check GitHub Actions tab for scan results
- Review GitGuardian dashboard for incidents

## Support

If credentials were exposed for more than 24 hours:
1. Assume they may have been compromised
2. Check Redis Cloud logs for unauthorized access
3. Consider creating a new Redis instance
4. Review your security policies

---

**Created:** February 17, 2026
**Status:** Action Required
