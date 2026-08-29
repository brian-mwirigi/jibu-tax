# Git Collaboration & Pull Request Policy

> **CRITICAL RULE FOR ALL 6 ENGINEERS:**  
> **NEVER push or merge directly to `main`.**  
> All work must happen on dedicated feature branches and be submitted via Pull Requests (PRs) for review.

---

## 🌿 Branching Strategy

1. **Branch Naming Convention:**
   - Role 1: `feat/role1-mcp-infra`
   - Role 2: `feat/role2-audio-orchestrator`
   - Role 3: `feat/role3-etims-simulator`
   - Role 4: `feat/role4-agent-routing`
   - Role 5: `feat/role5-ledger-filing`
   - Role 6: `feat/role6-telemetry-dashboard`
   - Bug fixes: `fix/<issue-name>`

2. **Standard Workflow:**
   ```bash
   # 1. Ensure you are up to date with origin/main
   git checkout main
   git pull origin main

   # 2. Create your feature branch
   git checkout -b feat/your-feature-name

   # 3. Work on your files, commit
   git add .
   git commit -m "feat(scope): descriptive title"

   # 4. Push your branch to GitHub
   git push -u origin feat/your-feature-name

   # 5. Create Pull Request using GitHub CLI or UI
   gh pr create --base main --head feat/your-feature-name --title "..." --body "..."
   ```

3. **PR Merge Rules:**
   - Do NOT merge your own PR without team visibility.
   - PRs must have clear descriptions and verification notes.
