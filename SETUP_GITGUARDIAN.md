# Setting Up GitGuardian Secret Scanning

## Why GitGuardian?

GitGuardian is a powerful secret detection tool that:
- Scans your entire Git history for leaked credentials
- Detects 350+ types of secrets (API keys, passwords, tokens, etc.)
- Provides real-time alerts on new commits
- Integrates seamlessly with GitHub Actions

## Quick Setup (5 minutes)

### Step 1: Sign Up for GitGuardian

1. Go to https://www.gitguardian.com/
2. Click "Start for Free"
3. Sign up with your GitHub account (recommended) or email
4. Verify your email address

### Step 2: Get Your API Key

1. Log into GitGuardian dashboard
2. Click on your profile (top right)
3. Go to "API" or "Settings" → "API Keys"
4. Click "Create API Key"
5. Give it a name: `GitHub Actions - event-driven-platform`
6. Copy the API key (you'll only see it once!)

### Step 3: Add API Key to GitHub

1. Go to your GitHub repository
2. Click "Settings" (repository settings, not your profile)
3. In the left sidebar, click "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Fill in:
   - **Name:** `GITGUARDIAN_API_KEY`
   - **Secret:** Paste your GitGuardian API key
6. Click "Add secret"

### Step 4: Verify Setup

1. Go to "Actions" tab in your repository
2. Find the latest "GitGuardian Secret Scan" workflow
3. Click "Re-run all jobs"
4. Wait for the scan to complete
5. Check the results - should show "✅ No critical secrets detected"

## What Gets Scanned?

The GitGuardian workflow scans for:

- **API Keys:** AWS, Google Cloud, Azure, Stripe, etc.
- **Database Credentials:** Redis, MongoDB, PostgreSQL, MySQL
- **Authentication Tokens:** JWT, OAuth, GitHub tokens
- **Private Keys:** SSH keys, SSL certificates, PGP keys
- **Cloud Credentials:** AWS access keys, GCP service accounts
- **And 350+ more secret types**

## Workflow Behavior

### When It Runs

- ✅ On every push to `main` or `develop` branches
- ✅ On every pull request to `main` or `develop`
- ✅ Weekly scheduled scan (Mondays at 2 AM UTC)
- ✅ Manual trigger (Actions tab → Run workflow)

### What Happens If Secrets Are Found

1. **Build fails** - The workflow will fail with exit code 1
2. **Notification** - You'll get a GitHub notification
3. **Details** - Check the workflow logs for:
   - What secret was found
   - Where it was found (file and line)
   - When it was committed
   - Severity level

### If Build Fails

```bash
# 1. Check the workflow logs
# 2. Identify the leaked secret
# 3. Rotate the credential immediately
# 4. Run the cleanup script
./remove_secrets.sh

# 5. Force push cleaned history
git push --force --all
```

## GitGuardian Dashboard

After setup, you can:

1. **View all incidents** - See every secret detected
2. **Set up integrations** - Slack, email, webhooks
3. **Configure policies** - Customize what gets detected
4. **Track remediation** - Mark secrets as resolved
5. **View analytics** - See trends over time

### Accessing the Dashboard

1. Go to https://dashboard.gitguardian.com/
2. Log in with your account
3. Select your workspace
4. View "Incidents" for detected secrets

## Multiple Scanners

Our workflow uses three scanners for comprehensive coverage:

| Scanner | Purpose | Requires Setup |
|---------|---------|----------------|
| **GitGuardian** | Primary scanner, 350+ secret types | ✅ Yes (API key) |
| **Gitleaks** | Fast, open-source scanner | ❌ No |
| **TruffleHog** | Verified secrets only | ❌ No |

Even without GitGuardian API key, Gitleaks and TruffleHog will still run!

## Troubleshooting

### "Invalid GitGuardian API key"

**Cause:** API key not set or incorrect

**Solution:**
1. Verify the secret name is exactly `GITGUARDIAN_API_KEY`
2. Check the API key is still valid in GitGuardian dashboard
3. Try regenerating the API key

### "GitGuardian scan skipped"

**Cause:** API key not configured (this is expected)

**Solution:**
- Follow steps above to add the API key
- Or ignore - other scanners (Gitleaks, TruffleHog) will still run

### "Rate limit exceeded"

**Cause:** Too many scans in a short time (free tier limit)

**Solution:**
1. Wait a few minutes
2. Consider upgrading to paid plan for higher limits
3. Reduce scan frequency in workflow

### Workflow fails but no secrets shown

**Cause:** Network issue or GitGuardian service down

**Solution:**
1. Check GitGuardian status: https://status.gitguardian.com/
2. Re-run the workflow
3. Check workflow logs for detailed error

## Free Tier Limits

GitGuardian free tier includes:

- ✅ Unlimited public repositories
- ✅ 1 private repository
- ✅ 25 developers
- ✅ 350+ secret types
- ✅ GitHub integration
- ⚠️ Limited API calls per month

For this project (public repo), you're covered by the free tier!

## Best Practices

### 1. Enable Branch Protection

```
Settings → Branches → Add rule for 'main'
☑ Require status checks to pass before merging
☑ Require "GitGuardian Secret Scanning" to pass
```

### 2. Set Up Notifications

In GitGuardian dashboard:
1. Go to Settings → Notifications
2. Add your email
3. Enable Slack integration (optional)
4. Set severity threshold (recommend: High and Critical)

### 3. Regular Audits

- Review GitGuardian dashboard weekly
- Check for false positives
- Update ignore patterns if needed
- Verify old incidents are resolved

### 4. Team Training

- Share this guide with team members
- Explain why secrets in code are dangerous
- Show how to use `.env` files properly
- Demonstrate the cleanup process

## Advanced Configuration

### Custom Ignore Patterns

Create `.gitguardian.yaml` in repository root:

```yaml
version: 2

paths-ignore:
  - "**/*.md"  # Ignore markdown files
  - "**/test_*.py"  # Ignore test files
  - "**/*.example"  # Ignore example files

matches-ignore:
  - name: Generic Password
    match: your-password  # Ignore placeholder passwords
```

### Scan Specific Paths Only

Update `.github/workflows/secret-scan.yml`:

```yaml
- name: GitGuardian Scan
  uses: GitGuardian/ggshield-action@v1
  with:
    args: --all-policies --verbose scan path backend/
```

## Cost Comparison

| Plan | Price | Features |
|------|-------|----------|
| **Free** | $0/month | 1 private repo, 25 devs, public repos unlimited |
| **Team** | $18/dev/month | Unlimited repos, advanced features |
| **Enterprise** | Custom | SSO, SLA, dedicated support |

For this project, **Free tier is sufficient**!

## Support

- **Documentation:** https://docs.gitguardian.com/
- **Community:** https://community.gitguardian.com/
- **Support:** support@gitguardian.com
- **Status:** https://status.gitguardian.com/

## Quick Reference

```bash
# Check if API key is set
gh secret list | grep GITGUARDIAN_API_KEY

# Manually trigger scan
gh workflow run secret-scan.yml

# View latest scan results
gh run list --workflow=secret-scan.yml --limit 1

# Download scan artifacts
gh run download <run-id>
```

## Next Steps

After setting up GitGuardian:

1. ✅ Run a full repository scan
2. ✅ Review and resolve any incidents
3. ✅ Enable branch protection rules
4. ✅ Set up notifications
5. ✅ Share this guide with your team
6. ✅ Schedule regular security reviews

---

**Setup Time:** 5 minutes  
**Cost:** Free  
**Benefit:** Prevent credential leaks forever  
**Priority:** HIGH

**Questions?** See `URGENT_SECURITY_ACTIONS.md` for more security guidance.
