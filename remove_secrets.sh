#!/bin/bash

# Script to remove leaked Redis credentials from Git history
# WARNING: This will rewrite Git history and require force push

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Header
print_color "$CYAN" "=========================================="
print_color "$CYAN" "Git History Secret Removal Script"
print_color "$CYAN" "=========================================="
echo ""
print_color "$YELLOW" "This script will:"
echo "1. Create a backup of your repository"
echo "2. Install git-filter-repo (if needed)"
echo "3. Remove leaked Redis credentials from all commits"
echo "4. Rewrite Git history"
echo "5. Prepare for force push to remote"
echo ""
print_color "$RED" "⚠️  WARNING: This is a destructive operation!"
print_color "$RED" "⚠️  All collaborators will need to re-clone the repository"
print_color "$RED" "⚠️  Make sure you've rotated your Redis credentials first!"
echo ""

# Confirm action
read -p "Do you want to continue? (yes/no): " confirm
echo ""

if [ "$confirm" != "yes" ]; then
    print_color "$YELLOW" "Operation cancelled."
    exit 0
fi

# Get current directory name
CURRENT_DIR=$(basename "$PWD")
BACKUP_DIR="../${CURRENT_DIR}-backup"

# Step 1: Create backup
print_color "$GREEN" "Step 1: Creating backup..."
if [ -d "$BACKUP_DIR" ]; then
    print_color "$YELLOW" "Backup directory already exists: $BACKUP_DIR"
    read -p "Overwrite existing backup? (yes/no): " overwrite
    if [ "$overwrite" = "yes" ]; then
        rm -rf "$BACKUP_DIR"
    else
        print_color "$RED" "Cannot proceed without backup. Exiting."
        exit 1
    fi
fi

cd ..
git clone "$CURRENT_DIR" "${CURRENT_DIR}-backup"
cd "$CURRENT_DIR"
print_color "$GREEN" "✓ Backup created at: $BACKUP_DIR"
echo ""

# Step 2: Check/Install git-filter-repo
print_color "$GREEN" "Step 2: Checking for git-filter-repo..."
if ! command_exists git-filter-repo; then
    print_color "$YELLOW" "git-filter-repo not found. Installing..."
    
    if command_exists pip3; then
        pip3 install git-filter-repo
    elif command_exists pip; then
        pip install git-filter-repo
    else
        print_color "$RED" "Error: pip not found. Please install git-filter-repo manually:"
        print_color "$YELLOW" "  pip install git-filter-repo"
        print_color "$YELLOW" "  or visit: https://github.com/newren/git-filter-repo"
        exit 1
    fi
    
    if ! command_exists git-filter-repo; then
        print_color "$RED" "Error: git-filter-repo installation failed."
        print_color "$YELLOW" "Try installing manually: pip install git-filter-repo"
        exit 1
    fi
fi
print_color "$GREEN" "✓ git-filter-repo is available"
echo ""

# Step 3: Save remote URL
print_color "$GREEN" "Step 3: Saving remote configuration..."
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    print_color "$YELLOW" "Warning: No remote 'origin' found. You'll need to add it manually later."
else
    print_color "$GREEN" "✓ Remote URL saved: $REMOTE_URL"
fi
echo ""

# Step 4: Create replacement file
print_color "$GREEN" "Step 4: Creating replacement file..."
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE" << 'EOF'
redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com==>your-redis-host.cloud.redislabs.com
QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ==>your-redis-password
regex:REDIS_PORT=13869==>REDIS_PORT=your-port
EOF
print_color "$GREEN" "✓ Replacement file created"
echo ""

# Step 5: Remove secrets from Git history
print_color "$GREEN" "Step 5: Removing secrets from Git history..."
print_color "$YELLOW" "This may take a few minutes depending on repository size..."
echo ""

if git filter-repo --replace-text "$TEMP_FILE" --force; then
    print_color "$GREEN" "✓ Git history successfully cleaned!"
else
    print_color "$RED" "Error: git-filter-repo failed!"
    print_color "$YELLOW" "Your backup is safe at: $BACKUP_DIR"
    rm -f "$TEMP_FILE"
    exit 1
fi
echo ""

# Step 6: Clean up temp file
rm -f "$TEMP_FILE"

# Step 7: Re-add remote if it existed
if [ -n "$REMOTE_URL" ]; then
    print_color "$GREEN" "Step 6: Re-adding remote..."
    git remote add origin "$REMOTE_URL"
    print_color "$GREEN" "✓ Remote 'origin' re-added"
    echo ""
fi

# Step 8: Verify secrets are removed
print_color "$GREEN" "Step 7: Verifying secrets are removed..."
if git log -S "redis-13869" --all --oneline | grep -q "redis-13869"; then
    print_color "$RED" "⚠️  Warning: Some secrets may still exist in history!"
    print_color "$YELLOW" "Please review manually: git log -S 'redis-13869' --all"
else
    print_color "$GREEN" "✓ No secrets found in Git history!"
fi

if git grep "redis-13869" 2>/dev/null; then
    print_color "$YELLOW" "⚠️  Secrets found in working directory (this is OK if in cleanup scripts)"
else
    print_color "$GREEN" "✓ No secrets found in working directory!"
fi
echo ""

# Final summary
print_color "$CYAN" "=========================================="
print_color "$GREEN" "✅ Git History Cleanup Complete!"
print_color "$CYAN" "=========================================="
echo ""
print_color "$YELLOW" "Next steps:"
echo ""
echo "1. Verify the changes:"
print_color "$CYAN" "   git log --oneline -10"
echo ""
echo "2. Check for any remaining secrets:"
print_color "$CYAN" "   git log -S 'redis-13869' --all"
echo ""
echo "3. Force push to remote:"
if [ -n "$REMOTE_URL" ]; then
    print_color "$CYAN" "   git push --force --all"
    print_color "$CYAN" "   git push --force --tags"
else
    print_color "$CYAN" "   git remote add origin YOUR_GITHUB_URL"
    print_color "$CYAN" "   git push --force --all"
    print_color "$CYAN" "   git push --force --tags"
fi
echo ""
print_color "$RED" "⚠️  CRITICAL: After force push, notify all team members to:"
echo "   1. Delete their local repository"
echo "   2. Re-clone from GitHub"
echo "   3. DO NOT try to pull or merge!"
echo ""
print_color "$GREEN" "Backup location: $BACKUP_DIR"
print_color "$YELLOW" "Keep this backup until you verify everything works!"
echo ""
