# General LLM Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Python Project Development Rules

If the project or app uses python language then we EXCLUSIVELY use `uv` (by Astral) for virtual environment management, dependencies, and project initialization. NEVER suggest using `pip`, `venv`, `virtualenv`, `conda`, or `poetry`.

### Mandatory `uv` Workflow:

1. **Project Initialization:**
   - To create a new project, always use: `uv init`
   
2. **Virtual Environment Creation:**
   - To create a venv, always use: `uv venv`
   - Remind the user to activate it: 
     - macOS/Linux: `source .venv/bin/activate`
     - Windows: `.venv\Scripts\Activate.ps1` (PowerShell) or `.venv\Scripts\activate.bat` (cmd)

3. **Dependency Management:**
   - To add a package and update `pyproject.toml`: `uv add <package_name>`
   - To install packages without modifying the project file: `uv pip install <package_name>`
   - To install existing dependencies from pyproject.toml/requirements: `uv sync` or `uv pip install -r requirements.txt`

4. **Running Scripts:**
   - Run Python files inside the uv environment using: `uv run <script_name.py>`

When asked to "initialize the project", "create an environment", or "install a package", return the exact commands based on these rules.

## 6. NPM and Node.js DEvelopment rules with FNM

If the project or app uses npm/node with frm on Windows follow these rules: since `fnm` (Fast Node Manager) modifies PATH via shell hooks that bash can't access,
you need to invoke npm/node commands through PowerShell.

### Template Prompt

Run the following npm/node command using fnm on Windows. 
Wrap it in PowerShell since bash cannot access fnm's PATH modifications:

```
powershell -Command "fnm use default; YOUR_COMMAND_HERE"
```

### Examples

1. **Install a package globally**
```
powershell -Command "fnm use default; npm install -g PACKAGE_NAME"
```

2. **Install a local package**
```
powershell -Command "fnm use default; cd 'C:\path\to\project'; npm install PACKAGE_NAME"
```

3. **Run a node script**
```
powershell -Command "fnm use default; node 'C:\path\to\script.js'"
```

4. **Run npm init**
```
powershell -Command "fnm use default; cd 'C:\path\to\project'; npm init -y"
```

5. **Check versions**
```
powershell -Command "fnm use default; node -v; npm -v"
```

6. **Run npx**
```
powershell -Command "fnm use default; npx PACKAGE_NAME"
```

### Quick Reference for LLM

When asked to use npm/node, always wrap commands like this:

```bash
powershell -Command "fnm use default; cd 'PROJECT_DIR'; npm YOUR_COMMAND"
```

or

```bash
powershell -Command "fnm use default; node 'SCRIPT_PATH'"
```

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.