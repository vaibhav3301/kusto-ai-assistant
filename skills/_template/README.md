# Skill Template

Use this template to create a new skill for your team's data.

## Steps to create a new skill

1. Copy this `_template` folder and rename it (e.g., `my-team-name`)
2. Edit `context.md` with your cluster/table/column details
3. Edit `sample-questions.md` with questions relevant to your data
4. Edit this `README.md` with your skill description
5. Commit and share with your team!

## What goes in each file

### context.md (REQUIRED)
This is the most important file. It tells the AI assistant:
- Which Kusto clusters and databases to connect to
- What tables exist and what data they contain
- What the columns mean (especially if names are cryptic)
- Any special patterns (e.g., JSON columns that need parse_json())
- Tips and gotchas specific to your data

### sample-questions.md (RECOMMENDED)
Example questions that PMs on your team commonly ask. This helps:
- New team members know what's possible
- The AI assistant understand what kind of queries to generate
- Build a shared knowledge base of useful analyses

### README.md (OPTIONAL)
A description of the skill and how to use it.

## Tips for writing good context

1. **Be specific about table structure** - If data is in JSON columns, show
   exactly how to parse it with an example query
2. **Explain domain terms** - What does "DatasourceType" mean? What are the
   possible values?
3. **Include common filters** - "Always filter by TIMESTAMP > ago(7d)"
4. **Note gotchas** - "This table has a 2-hour data delay" or "Test data has
   vault names containing 'BVT'"
