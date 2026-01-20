#!/bin/bash
# Push Cursor MCP to GitHub - Interactive Script

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  CURSOR MCP - GITHUB UPLOAD SCRIPT                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd /home/kr/Desktop/cursor-mcp || exit 1

echo "Current Status:"
echo "  Commit: $(git log --oneline -1)"
echo "  Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "  Files ready: $(git ls-tree -r HEAD | wc -l) files"
echo ""

# Check if repository exists on GitHub
echo "Checking GitHub repository..."
REPO_CHECK=$(curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/KofiRusu/mcp-serv)

if [ "$REPO_CHECK" = "200" ]; then
    echo "✅ Repository exists on GitHub"
else
    echo "⚠️  Repository not found (HTTP $REPO_CHECK)"
    echo ""
    echo "Create it at: https://github.com/new"
    echo "  - Repository name: mcp-serv"
    echo "  - Description: Cursor MCP - Persistent Cross-Chat Memory System"
    echo "  - Public repository"
    echo ""
    read -p "Press ENTER after creating the repository..."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Choose Authentication Method:"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "1) Personal Access Token (HTTPS) - Easiest"
echo "2) GitHub CLI - Recommended if installed"
echo "3) SSH Key - Most secure (if configured)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📋 Using Personal Access Token (HTTPS)"
        echo ""
        echo "1. Go to: https://github.com/settings/tokens"
        echo "2. Click 'Generate new token (classic)'"
        echo "3. Select scope: repo (full control of private repos)"
        echo "4. Generate and copy the token"
        echo ""
        read -s -p "Paste your Personal Access Token: " TOKEN
        echo ""
        
        if [ -z "$TOKEN" ]; then
            echo "❌ No token provided"
            exit 1
        fi
        
        echo "Pushing with HTTPS..."
        git remote set-url origin https://KofiRusu:${TOKEN}@github.com/KofiRusu/mcp-serv.git
        git push -u origin main
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Successfully pushed to GitHub!"
            echo "Repository: https://github.com/KofiRusu/mcp-serv"
        else
            echo "❌ Push failed"
            exit 1
        fi
        ;;
    2)
        echo ""
        echo "📋 Using GitHub CLI"
        echo ""
        
        if ! command -v gh &> /dev/null; then
            echo "❌ GitHub CLI not installed"
            echo "Install with: sudo apt install gh"
            exit 1
        fi
        
        echo "Authenticating with GitHub..."
        gh auth login || exit 1
        
        echo "Pushing with GitHub CLI..."
        git remote set-url origin https://github.com/KofiRusu/mcp-serv.git
        gh repo create mcp-serv --source=. --remote=origin --push 2>/dev/null || git push -u origin main
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Successfully pushed to GitHub!"
            echo "Repository: https://github.com/KofiRusu/mcp-serv"
        else
            echo "❌ Push failed"
            exit 1
        fi
        ;;
    3)
        echo ""
        echo "🔑 Using SSH Key"
        echo ""
        
        if [ ! -f ~/.ssh/id_ed25519 ]; then
            echo "Generating SSH key..."
            ssh-keygen -t ed25519 -C "kofirusu@gmail.com" -N "" -f ~/.ssh/id_ed25519
        fi
        
        echo ""
        echo "Add this public key to GitHub:"
        echo "👉 https://github.com/settings/keys"
        echo ""
        echo "Public Key:"
        cat ~/.ssh/id_ed25519.pub
        echo ""
        
        read -p "Press ENTER after adding the key to GitHub..."
        
        echo "Pushing with SSH..."
        git remote set-url origin git@github.com:KofiRusu/mcp-serv.git
        git push -u origin main
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Successfully pushed to GitHub!"
            echo "Repository: https://github.com/KofiRusu/mcp-serv"
        else
            echo "❌ Push failed"
            exit 1
        fi
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Upload complete! Your code is now on GitHub:"
echo "https://github.com/KofiRusu/mcp-serv"
echo "═══════════════════════════════════════════════════════════════"
