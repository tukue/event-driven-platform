#!/bin/bash

# Script to remove leaked Redis credentials from Git history
# WARNING: This will rewrite Git history and require force push

echo "=========================================="
echo "Git History Secret Removal Script"
echo "=========================================="
echo ""
echo "This script will:"
echo "1. Remove leaked Redis credentials from all commits"
echo "2. Rewrite Git history"
echo "3. Require force push to remote"
echo ""
echo "⚠️  WARNING: This is a destructive operation!"
echo "⚠️  All collaborators will need to re-clone the repository"
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

echo ""
echo "Step 1: Creating backup..."
cd ..
git clone event-driven-platform event-driven-platform-backup
cd event-driven-platform

echo ""
echo "Step 2: Installing git-filter-repo (if needed)..."
if ! command -v git-filter-repo &> /dev/null; then
    echo "Installing git-filter-repo via pip..."
    pip install git-filter-repo
fi

echo ""
echo "Step 3: Creating replacement file..."
cat > /tmp/secrets-to-remove.txt << 'EOF'
redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com==>your-redis-host.cloud.redislabs.com
QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ==>your-redis-password
regex:REDIS_HOST=redis-\d+\.crce\d+\.eu-north-1-1\.ec2\.cloud\.redislabs\.com==>REDIS_HOST=your-redis-host.cloud.redislabs.com
regex:REDIS_PORT=13869==>REDIS_PORT=your-port
EOF

echo ""
echo "Step 4: Removing secrets from Git history..."
git filter-repo --replace-text /tmp/secrets-to-remove.txt --force

echo ""
echo "Step 5: Cleaning up..."
rm /tmp/secrets-to-remove.txt

echo ""
echo "=========================================="
echo "✅ Git history has been cleaned!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify the changes: git log --all --oneline"
echo "2. Check files: git grep 'redis-13869' \$(git rev-list --all) || echo 'No secrets found!'"
echo "3. Force push: git push --force --all"
echo "4. Force push tags: git push --force --tags"
echo ""
echo "⚠️  IMPORTANT: Notify all team members to:"
echo "   - Delete their local repository"
echo "   - Re-clone from GitHub"
echo ""
echo "Backup location: ../event-driven-platform-backup"
